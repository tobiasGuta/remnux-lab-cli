# Security model

This project reduces exposure while investigating potentially malicious files; it cannot promise perfect isolation.

## Intended boundaries

- The managed libvirt domain is **exactly** `remnux-lab` on `qemu:///system`.
- Provisioning uses `--network none` and a VNC listener bound to `127.0.0.1`.
- The CLI refuses a domain configuration with virtual network interfaces, host filesystems, passthrough devices, guest agent channels, extra disks, or non-loopback graphical listeners.
- A sample is moved into a guest only through an ISO9660 file attached as read-only virtual media while the guest is powered off; the host never extracts the sample.
- The guest is restored to `clean-hardened` after an investigation, only after validating its stored domain configuration.
- `doctor` and `snapshots` inspect configuration and host prerequisites without calling mutating libvirt operations.

## Default guest channels and the `harden` repair

Some versions of virt-install/libvirt provision a host-guest communication channel
in otherwise offline domains. The CLI intentionally treats a channel as a failed
isolation check, even when there is no virtual NIC. To inspect what is present:

```bash
sudo virsh dumpxml --inactive remnux-lab | grep -A8 -B2 '<channel'
```

If the VM is shut off and the only channel is a recognized QEMU guest-agent or
SPICE/vdagent channel, `malware-lab.sh harden` can remove it **after an interactive
confirmation**. The command does not touch disks or snapshots and saves a copy
of the previous VM XML in the VM's `config-backups` directory. Unknown or
multiple channels require manual review; the CLI will not silently allow them.

**Snapshot protections:** Preserve any older `clean-base` snapshot but create `clean-hardened` only after the guest is clean, shut off, and hardened. The CLI verifies the snapshot XML embeds the expected offline VM configuration and will not restore a snapshot with unexpected networking, passthrough, channels, or running state. It never falls back to `clean-base`.

## Limitations

- A hypervisor or kernel vulnerability may allow escape. Use a **physically separate, network-isolated machine** for samples that require high assurance.
- Read-only media prevents guest writes to the ISO; it does not prevent malicious behavior by a file opened in the guest.
- Host-side sample files and generated ISOs remain on your disk after `reset`. Handle them according to your retention policy.
- Snapshots are not host backups. Back up critical host files independently.
- Software updates inside an offline guest require deliberate maintenance while it is clean and no sample is present. Never attach an infected guest to your personal network.
- Tools running with `sudo` and libvirt still require a trusted host. Review scripts before execution.
- Graphics clients and host peripherals remain potential attack surfaces. Keep Fedora, libvirt, and QEMU updated.
- The CLI is not an enforcement mechanism for modifications made by an administrator outside the CLI.

## Operational guidance

1. Validate downloads and keep the host and hypervisor patched.
2. Configure analysis tools **before** importing suspicious files; then create the offline `clean-hardened` snapshot.
3. Verify `malware-lab.sh status` and check the guest has no network interface.
4. Import an unmodified sample while the VM is shut down. Inspect it only inside the guest.
5. Preserve any results outside the VM through a carefully reviewed, separate workflow **before** reset; do not mount your home directory in the guest.
6. Revert the guest snapshot and verify its state before a new investigation.
