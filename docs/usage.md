# Usage and recovery

## Deploy

```bash
bash scripts/setup-remnux-lab.sh --storage-dir /absolute/directory --memory 4096 --cpus 2
```

The directory must already exist. The installer checks storage type, installs packages, enables modular libvirt storage/QEMU sockets on modern Fedora, verifies the official image, labels the VM directory for SELinux, and imports a single offline domain. It refuses to overwrite an existing `remnux-lab` domain or unverified disk.

If provisioning fails after the download, resolve the error and rerun the same command; the verified file is reused. Never remove unrelated VMs or storage pools to fix an installation error.

## Initialize baseline

Boot the appliance and inspect the desktop, then shut it down and wait for `shut off`:

```bash
sudo virsh start remnux-lab
virt-viewer --connect qemu:///system remnux-lab
sudo virsh shutdown remnux-lab
sudo virsh domstate remnux-lab
sudo virsh snapshot-create-as remnux-lab clean-base \
  --description 'Clean offline REMnux environment'
```

Create the baseline **before** introducing suspicious files. A snapshot can only be considered clean if the guest is actually clean when it is taken.

## Manage

Install the CLI with `bash install.sh`, then:

```bash
malware-lab.sh status
malware-lab.sh start
sudo virsh shutdown remnux-lab
malware-lab.sh import /absolute/path/to/sample.zip
malware-lab.sh start
malware-lab.sh reset
```

The `import` command requires a shut-off VM and the `clean-base` snapshot. The ISO is stored under the VM disk directory in `imports/` and remains after reset. It can be mounted or accessed from the virtual optical drive inside REMnux.

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
