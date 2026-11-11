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
- Typed confirmation before destructive snapshot recovery.
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

# Inspect guest boot; once clean and powered off, make a baseline:
virt-viewer --connect qemu:///system remnux-lab
sudo virsh shutdown remnux-lab
sudo virsh domstate remnux-lab           # Must say: shut off
sudo virsh snapshot-create-as remnux-lab clean-base \
  --description 'Clean offline REMnux environment'

# Install the CLI entry point:
bash install.sh
malware-lab.sh status
```

If you already have a working `remnux-lab` VM, **skip the provisioning script**. Install the CLI only. It discovers the existing VM disk location from libvirt, so no workstation-specific path is necessary.

## Everyday commands

```bash
malware-lab.sh start                       # Boot with safety checks; open viewer
malware-lab.sh start --no-viewer           # Boot without opening viewer
malware-lab.sh status                      # Inspect offline status, devices, snapshot
malware-lab.sh import /path/to/sample.zip  # VM must be shut off; no host extraction
malware-lab.sh reset                       # Typed confirmation required
```

`import` creates a read-only ISO from the unmodified input file and attaches it to the powered-off VM. Reboot the guest and access its virtual CD-ROM. Do not enable shared folders or guest networking to transfer samples.

`reset` **discards guest changes** made since `clean-base`, including analysis results saved only in the guest. It does not delete other VMs or remove host-side imported files.

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
