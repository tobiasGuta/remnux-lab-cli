#!/usr/bin/env bash
# Provision a dedicated, offline REMnux appliance on Fedora using system libvirt.
set -Eeuo pipefail

readonly VM='remnux-lab'
readonly URI='qemu:///system'
readonly SOURCE_URL='https://download.remnux.org/202610b/remnux-noble-amd64-proxmox.qcow2'
readonly SOURCE_SHA256='9ef87306cd9b982de9109d08627040a15b2eb9d75040c9ceeffabce1a0004568'
readonly SOURCE_FILENAME='remnux-noble-amd64-proxmox.qcow2'
readonly DISK_FILENAME='remnux-noble-amd64.qcow2'

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  cat <<'HELP'
Usage: setup-remnux-lab.sh --storage-dir /absolute/path/to/VMs [--memory 4096] [--cpus 2]

Creates ONLY a new VM named remnux-lab, in STORAGE_DIR/remnux-lab.
The storage directory must exist on ext4, XFS, Btrfs, or F2FS.
Refuses to replace an existing VM or a modified/unverified disk image.

This pins the official October 2026 REMnux amd64 QCOW2 and its SHA-256.
See https://docs.remnux.org/install-distro/get-virtual-appliance
HELP
}

STORAGE=''
MEMORY=4096
CPUS=2
while (($#)); do
  case "$1" in
    --storage-dir) (($# >= 2)) || fail '--storage-dir requires a value'; STORAGE="$2"; shift 2 ;;
    --memory) (($# >= 2)) || fail '--memory requires a value'; MEMORY="$2"; shift 2 ;;
    --cpus) (($# >= 2)) || fail '--cpus requires a value'; CPUS="$2"; shift 2 ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; fail "Unknown argument: $1" ;;
  esac
done

[[ -n "$STORAGE" ]] || { usage >&2; fail 'Specify --storage-dir.'; }
[[ "$STORAGE" == /* ]] || fail '--storage-dir must be absolute.'
[[ -d "$STORAGE" ]] || fail "Storage directory not found: $STORAGE"
STORAGE="$(realpath -e -- "$STORAGE")"
[[ "$STORAGE" != *$'\n'* && "$STORAGE" != *','* ]] || fail 'Storage path contains unsupported characters.'
[[ "$MEMORY" =~ ^[0-9]+$ && "$MEMORY" -ge 2048 ]] || fail 'Memory must be >= 2048 MiB.'
[[ "$CPUS" =~ ^[0-9]+$ && "$CPUS" -ge 1 && "$CPUS" -le 128 ]] || fail 'Invalid CPU count.'
[[ "$(uname -m)" == x86_64 ]] || fail 'This prebuilt appliance requires an x86_64 host.'

FSTYPE="$(findmnt -n -T "$STORAGE" -o FSTYPE)"
case "$FSTYPE" in ext4|xfs|btrfs|f2fs) ;; *) fail "Unsupported filesystem: $FSTYPE" ;; esac
LAB="$STORAGE/$VM"
DOWNLOAD="$LAB/$SOURCE_FILENAME"
DISK="$LAB/$DISK_FILENAME"
printf 'Lab: %s (%s)\n' "$LAB" "$FSTYPE"
df -h "$STORAGE"

# Only install standard Fedora virtualization packages; never alter other VMs.
sudo dnf install -y virt-install virt-viewer qemu-kvm qemu-img libvirt-daemon-kvm \
  policycoreutils-python-utils acl wget python3 xorriso qemu-ui-spice-core qemu-device-display-qxl
if systemctl list-unit-files virtqemud.socket --no-legend 2>/dev/null | grep -q '^virtqemud.socket'; then
  sudo systemctl enable --now virtqemud.socket virtstoraged.socket
else
  sudo systemctl enable --now libvirtd.service
fi
sudo virsh -c "$URI" list --all >/dev/null
sudo virsh -c "$URI" dominfo "$VM" >/dev/null 2>&1 && fail "VM $VM already exists. Nothing was replaced."
getent passwd qemu >/dev/null || fail 'Missing qemu service user.'
getent group qemu >/dev/null || fail 'Missing qemu service group.'

sudo install -d -m 0755 -o "$(id -un)" -g "$(id -gn)" "$LAB"
# Only grant QEMU traversal rights to the selected path and its ancestors.
parent="$LAB"
while [[ "$parent" != / ]]; do
  sudo setfacl -m u:qemu:--x "$parent"
  parent="$(dirname "$parent")"
done

if [[ -e "$DISK" && -e "$DOWNLOAD" ]]; then
  fail 'Both disk and download files exist. Inspect them; refusing to choose or overwrite.'
fi
if [[ -e "$DISK" ]]; then
  [[ -f "$DISK" && ! -L "$DISK" ]] || fail 'Disk must be a regular non-symlink file.'
  printf 'Checking existing image against the pinned official SHA-256...\n'
  printf '%s  %s\n' "$SOURCE_SHA256" "$DISK" | sudo sha256sum --check --status || fail 'Unverified existing disk; refusing to import.'
else
  [[ ! -L "$DOWNLOAD" ]] || fail 'Download path must not be a symlink.'
  printf 'Downloading the official REMnux QCOW2 (resumable)...\n'
  wget -c --show-progress -O "$DOWNLOAD" "$SOURCE_URL"
  printf '%s  %s\n' "$SOURCE_SHA256" "$DOWNLOAD" | sha256sum --check --status || fail 'Checksum mismatch; refusing to import.'
  mv -- "$DOWNLOAD" "$DISK"
fi
qemu-img info -- "$DISK"
sudo chown qemu:qemu "$DISK"
sudo chmod 0600 "$DISK"
sudo semanage fcontext -a -t virt_image_t "$LAB(/.*)?" 2>/dev/null || \
  sudo semanage fcontext -m -t virt_image_t "$LAB(/.*)?"
sudo restorecon -RF "$LAB"

# Generate an initial SPICE/QXL domain definition without starting the VM.
# virt-install may add guest-agent and USB-redirection devices by default;
# sanitize the candidate XML before `virsh define`, and refuse unknown devices.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CANDIDATE="$(mktemp --suffix=.xml)"
HARDENED="$(mktemp --suffix=.xml)"
trap 'rm -f -- "$CANDIDATE" "$HARDENED"' EXIT
# The temporary XML file belongs to the invoking user; only XML generation
# needs sudo. Shell redirection intentionally writes as the current user.
# shellcheck disable=SC2024
sudo virt-install --connect "$URI" --name "$VM" --virt-type kvm \
  --memory "$MEMORY" --vcpus "$CPUS" --import --osinfo ubuntu24.04 \
  --controller type=scsi,model=virtio-scsi \
  --disk "path=$DISK,format=qcow2,bus=scsi" \
  --network none --video qxl --graphics spice,listen=127.0.0.1 \
  --print-xml --dry-run > "$CANDIDATE"
python3 "$SCRIPT_DIR/sanitize-domain-xml.py" "$DISK" < "$CANDIDATE" > "$HARDENED" || \
  fail 'Generated VM configuration failed the offline security checks. Nothing was defined.'
sudo virsh -c "$URI" define "$HARDENED" || fail 'Could not define the validated offline domain.'

printf '\nCreated %s in a shut-off state with SPICE/QXL, no network or host sharing.\n' "$VM"
printf 'Validate: sudo virsh domiflist %s\n' "$VM"
printf 'Open the display after starting: virt-viewer --connect qemu:///system %s\n' "$VM"
printf 'Install CLI: bash install.sh; run: malware-lab.sh doctor\n'
printf 'After verifying a clean guest, shut down and create a clean-spice snapshot before importing samples.\n'