# Usage and recovery

## Deploy

```bash
bash scripts/setup-remnux-lab.sh --storage-dir /absolute/directory --memory 4096 --cpus 2
```

The directory must already exist. The installer checks storage type, installs packages, enables modular libvirt storage/QEMU sockets on modern Fedora, verifies the official image, labels the VM directory for SELinux, and imports a single offline domain. It refuses to overwrite an existing `remnux-lab` domain or unverified disk.

If provisioning fails after the download, resolve the error and rerun the same command; the verified file is reused. Never remove unrelated VMs or storage pools to fix an installation error.

## Initialize baseline

The installer creates a shut-off SPICE/QXL VM and removes generated SPICE agent
channels and USB redirection from its XML **before** defining the VM. No domain
is booted automatically. This is intentional: review its offline configuration
first, and do not launch a guest with unreviewed host integrations.

```bash
bash install.sh
malware-lab.sh status               # The missing snapshot message is expected
malware-lab.sh start                # Verify the graphical desktop
# From the guest when finished: sudo poweroff
sudo virsh domstate remnux-lab     # Must say: shut off
sudo virsh snapshot-create-as remnux-lab clean-spice \
  --description 'Clean offline REMnux with working SPICE/QXL graphics'
malware-lab.sh status
```

Create `clean-spice` **before** importing suspicious files and only after verifying
that the guest is clean, no virtual network/sharing devices are present, and any
test ISOs have been detached. Never replace or delete legacy snapshots as part
of this migration.

## Manage

For every command's syntax, prerequisites, example output, effects on the VM, and common errors, see the [complete CLI reference](cli-reference.md).

Install the CLI with `bash install.sh`, then:

```bash
malware-lab.sh status
malware-lab.sh doctor       # Read-only diagnostic report
malware-lab.sh snapshots    # Read-only snapshot inventory
malware-lab.sh start
sudo virsh shutdown remnux-lab
malware-lab.sh import /absolute/path/to/sample.zip
malware-lab.sh start
malware-lab.sh reset
```

The `import` command requires a shut-off VM and the `clean-spice` snapshot. The ISO is stored under the VM disk directory in `imports/` and remains after reset. It can be mounted or accessed from the virtual optical drive inside REMnux.

The `reset` command asks you to type `RESET remnux-lab`; it force-stops the VM if it is running, then reverts the snapshot. **Unsaved analysis data in the VM will be lost.** It never deletes the domain itself.

## Troubleshooting

**Failed to connect to `virtstoraged-sock`:**

```bash
sudo systemctl enable --now virtstoraged.socket
sudo virsh -c qemu:///system pool-list --all
```

**Missing permissions / SELinux issue:** Recheck mount type and the lab directory's `virt_image_t` context. Do not disable SELinux to work around permissions.

**Safety checks fail:** Examine `sudo virsh dumpxml remnux-lab` and `sudo virsh dumpxml --inactive remnux-lab`. Remove unsafe devices only after examining their purpose; the CLI will not silently repair configuration changes.

**Need a different storage location:** The CLI discovers the disk from the existing VM definition. The provisioning script's `--storage-dir` must point to your chosen existing directory and is intended for *initial creation only*.

## If `status` reports a host-guest channel

Some libvirt configurations insert a guest agent or display-agent channel even
when no network interface exists. Do **not** disable the safety check. With the
VM shut down, run:

```bash
malware-lab.sh harden
malware-lab.sh status
```

`harden` only supports a single recognized service channel and requires typed
confirmation. It saves a backup of the original libvirt XML, modifies only
`remnux-lab`, and never changes the disk or existing snapshots. The CLI refuses an unsafe, running, or unverifiable saved snapshot and does not fall back to `clean-base` or `clean-hardened`. To migrate from an older install, preserve both `clean-base` and `clean-hardened`, ensure the guest is clean and shut off, configure SPICE/QXL with sharing and redirection removed, detach imported media, and create `clean-spice`. Do not overwrite or delete existing snapshots.

## Read-only troubleshooting

Run `malware-lab.sh doctor` to check KVM availability, optional tools, SELinux status, storage filesystem/free space, the saved/live domain definition, and the `clean-spice` snapshot. `PASS` means that individual check succeeded; `WARN` means investigate a possible weakness or missing optional component; `FAIL` blocks a passing exit status. The command does not repair the VM or change system services. Note that `doctor` assumes the named VM exists and libvirt is reachable; connection failures require manually checking `sudo virsh -c qemu:///system dominfo remnux-lab`.

Use `malware-lab.sh snapshots` to list the snapshots for `remnux-lab` and verify the only approved reset target, `clean-spice`. It never reverts, creates, or deletes snapshots; an old `clean-base` is listed only for reference.

Use `sudo systemctl status virtstoraged.socket` for a missing storage socket, and inspect SELinux permissions rather than disabling policy.
