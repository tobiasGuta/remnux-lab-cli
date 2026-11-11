# remnux-lab-cli

**A Fedora-first command-line toolkit for provisioning and operating an offline REMnux malware-analysis VM with QEMU/KVM and libvirt.**

## Why this exists

Investigating suspicious files on a daily-use Linux workstation can expose personal data, attached drives, and trusted networks to unnecessary risk. Rebuilding an isolated investigation environment by hand is slow, inconsistent, and easy to misconfigure.

`remnux-lab-cli` makes that process **repeatable and inspectable**: verify an official REMnux appliance, provision a dedicated VM with no virtual network adapter, check its configuration before use, move samples through read-only media, and restore a known-clean snapshot between investigations. It is intended for defensive malware research, incident-response preparation, and digital forensics.

This is **risk reduction, not a guarantee of containment**. VM escapes and host vulnerabilities are possible. Use a dedicated analysis machine for higher-risk execution and maintain independent backups.

## Features

- Verified official REMnux amd64 QCOW2 download (pinned release and SHA-256).
- QEMU/KVM VM with **no virtual NIC**, host shares, or passthrough configured.
- CLI guardrails checking persistent and live libvirt XML.
- Offline single-file transfer using read-only ISO media.
- Snapshot-aware recovery: validate the saved VM configuration before typed confirmation and revert.
- Read-only `doctor` diagnostics and `snapshots` recovery inventory.
- Scoped to **one VM named `remnux-lab`**; does not enumerate or change other VMs.
- No malware samples, VM images, or personal environment paths tracked by Git.

## Requirements

Fedora Linux, x86-64 hardware virtualization (KVM), a Linux-native filesystem (Btrfs, ext4, XFS, or F2FS), system libvirt, `sudo`, and enough free space for the approximately 8 GB download plus a 100 GiB thin-provisioned virtual disk. The installer requires internet access **on the host only** for downloading a verified appliance and Fedora packages. The created guest has no virtual network adapter.

## Quick start

Clone this repository and provision the VM in a directory you choose:

```bash
git clone https://github.com/tobiasGuta/remnux-lab-cli.git
cd remnux-lab-cli

# Choose an existing directory on a Linux-native filesystem.
# Example: /var/lib/libvirt/images
bash scripts/setup-remnux-lab.sh --storage-dir /var/lib/libvirt/images

# Inspect the guest, shut it off, and remove any libvirt-added guest channel:
virt-viewer --connect qemu:///system remnux-lab
sudo virsh shutdown remnux-lab
sudo virsh domstate remnux-lab           # Must say: shut off
bash install.sh
malware-lab.sh status                   # If a channel is flagged, run: malware-lab.sh harden
# Once the VM is clean, shut off, and channel-free, make a baseline:
sudo virsh snapshot-create-as remnux-lab clean-hardened \
  --description 'Clean offline hardened REMnux environment'

# Check the snapshot and the VM definition:
malware-lab.sh status
```

If you already have a working `remnux-lab` VM, **skip the provisioning script**. Install the CLI only. It discovers the existing VM disk location from libvirt, so no workstation-specific path is necessary.

## Everyday commands

```bash
malware-lab.sh start                       # Boot with safety checks; open viewer
malware-lab.sh start --no-viewer           # Boot without opening viewer
malware-lab.sh status                      # Inspect offline status, devices, snapshot
malware-lab.sh doctor                      # Read-only host, storage and isolation diagnostics
malware-lab.sh snapshots                   # Read-only snapshot inventory and baseline validation
malware-lab.sh import /path/to/sample.zip  # VM must be shut off; no host extraction
malware-lab.sh reset                       # Typed confirmation required
malware-lab.sh harden                      # Remove a recognized guest channel (confirmed)
```

`doctor` and `snapshots` are strictly read-only. A failed diagnostic exits nonzero; warnings identify weaker settings or missing optional tools. Neither command modifies the VM or its snapshots.

`import` creates a read-only ISO from the unmodified input file and attaches it to the powered-off VM. Reboot the guest and access its virtual CD-ROM. Do not enable shared folders or guest networking to transfer samples.

`reset` validates and restores only the offline `clean-hardened` snapshot; it **discards guest changes** made since that snapshot, including analysis results saved only in the guest. It does not delete other VMs or remove host-side imported files.

If `status` reports `host-guest channel`, your hypervisor added a guest-service
channel despite the offline VM configuration. With REMnux shut down, run
`malware-lab.sh harden` to review and remove a **single recognized** service
channel. It requires confirmation and does not touch disks, snapshots, or other
VMs. Create a new `clean-hardened` snapshot after removing the channel. The CLI refuses to restore unsafe or unverifiable snapshot configurations and never falls back to `clean-base`.

## Tests

Run the non-destructive local regression suite:

```bash
bash tests/smoke.sh
python3 tests/channel_policy.py
python3 tests/security_policy.py
python3 tests/diagnostics_policy.py
```

CI checks Bash 5.1 and 5.2 and runs the mocked libvirt tests against Python 3.11 and 3.13. No real VM is created in CI.

## Documentation

- [Usage and recovery](docs/usage.md)
- [Security model and limitations](docs/security.md)
- [Official REMnux appliance documentation](https://docs.remnux.org/install-distro/get-virtual-appliance)

## Scope

Version 0.1 is Fedora-first and intentionally manages only `remnux-lab` through `qemu:///system`. It does not promise perfect containment, dynamic malware detonation orchestration, or support for arbitrary hypervisors. All guest internet access and clipboard sharing are deliberately excluded.

## Contributing

Please open issues or pull requests for portability improvements, tests, and safer isolation checks. Never upload live malware, secrets, virtual disks, or private investigation data to this repository.

## License

MIT — see [LICENSE](LICENSE). Not affiliated with or endorsed by the REMnux project.
