# CLI reference

This guide describes the installed `malware-lab.sh` commands: what they do, when to use them, what they change, what output to expect, and how to recover from common errors.

## Scope and requirements

The CLI intentionally manages **only** the existing `remnux-lab` domain on `qemu:///system`. It does not select arbitrary VMs or touch unrelated domains. The REMnux disk must be a regular file named `remnux-noble-amd64.qcow2` in a directory named `remnux-lab`. Run the commands on the **Linux host**, not in the REMnux guest.

Install the CLI from the repository:

```bash
bash install.sh
malware-lab.sh help
```

The commands may prompt for your `sudo` password to query libvirt. `start`, `status`, `doctor`, and `snapshots` check the VM's offline isolation policy. An unsafe configuration is a reason to stop and investigate—not to disable a check.

A validated **`clean-spice`** snapshot is required for `import` and `reset`. The older `clean-base` and `clean-hardened` snapshots may still be listed, but **reset never uses them**. `clean-spice` must be a shut-off, offline SPICE/QXL VM snapshot with no attached sample CD-ROM.

## Command summary

| Command | Changes VM or host state? | Purpose |
| --- | --- | --- |
| `malware-lab.sh help` | No | Print supported commands and guardrails |
| `malware-lab.sh status` | No | Show VM state, disks, interfaces, and safety-policy result |
| `malware-lab.sh doctor` | No | Diagnose host requirements, isolation, and recovery baseline |
| `malware-lab.sh snapshots` | No | List snapshots and validate the only approved reset target |
| `malware-lab.sh start [--no-viewer]` | **Yes** | Power on the VM after isolation checks; optionally open viewer |
| `malware-lab.sh import FILE` | **Yes** | Create a host-side ISO and attach it as read-only media |
| `malware-lab.sh reset` | **Yes—destructive inside guest** | Confirm and revert `remnux-lab` to `clean-spice` |
| `malware-lab.sh harden` | **Yes** | Confirm and remove one recognized guest communication channel |

## `help` — show usage

```bash
malware-lab.sh help
```

**Before:** No VM needs to be running or even defined.  
**Result:** Prints syntax, allowed subcommands, and safety restrictions.  
**Common errors:** Unknown subcommands print help and exit with an error.

## `status` — check the VM before use

```bash
malware-lab.sh status
```

**Before:** The `remnux-lab` domain and disk must be accessible through system libvirt.  
**Result:** Prints its state (`running` or `shut off`), disk location, `clean-spice` snapshot status, network interfaces, and block devices. Checks persistent XML and, if running, active XML. Nothing is changed.

Typical ending:

```text
Snapshot:  clean-spice present (configuration verified)
Safety checks: PASS (offline, no shares/passthrough, no unexpected disks)
```

**If it fails:** An `SAFETY CHECK FAILED` message identifies a prohibited device or setting. Review `sudo virsh dumpxml --inactive remnux-lab`; do not bypass the check. If the snapshot is missing, `status` can report `clean-spice MISSING` while otherwise passing domain isolation: imports and resets still require a validated snapshot.

## `doctor` — host and lab health report

```bash
malware-lab.sh doctor
```

**Before:** Libvirt must be reachable and the VM must exist.  
**Result:** Checks `/dev/kvm`; selected dependencies (`xorriso`, `virt-xml`, `restorecon`, `virt-viewer`, `findmnt`, `df`); SELinux; libvirt storage service; filesystem and available space; persistent and live isolation policy; and `clean-spice` snapshot metadata. Read-only.

Possible report:

```text
[PASS] SELinux enforcing
[PASS] Saved VM configuration passes offline isolation policy
[PASS] Recovery snapshot clean-spice is present and policy-verified
Diagnostic summary: 0 failure(s), 0 warning(s)
```

`PASS` means a specific check passed; `WARN` indicates a potential weakness or missing optional component; `FAIL` makes the command exit nonzero. Warnings alone do not necessarily make it fail. The command **does not install dependencies or repair anything**.

## `snapshots` — view recovery points

```bash
malware-lab.sh snapshots
```

**Before:** System libvirt must be accessible. A valid `clean-spice` snapshot is necessary for successful verification.  
**Result:** Lists the snapshots belonging to `remnux-lab`, then checks that `clean-spice` is a shut-off, offline, SPICE/QXL snapshot without unexpected devices or attached removable media. Also checks current VM isolation. Read-only.

Expected ending:

```text
Verified reset target: clean-spice (shut-off, offline domain configuration)
```

**If it fails:** The baseline may be absent or have unsafe/missing metadata. The CLI will not automatically fall back to legacy snapshots; inspect the result before attempting any reset.

## `start` — boot the offline lab

```bash
malware-lab.sh start
malware-lab.sh start --no-viewer
```

**Before:** The saved configuration must pass offline isolation checks. If already running, the live configuration must pass too.  
**Result:** Starts only `remnux-lab` when shut off, rechecks isolation, and normally opens `virt-viewer`. If the VM is already running, it reports that rather than creating a second instance. `--no-viewer` skips opening the graphical window.

Typical output:

```text
Starting remnux-lab without networking...
Domain 'remnux-lab' started
Isolation verification passed.
```

**If it fails:** Unsafe XML, missing disk, inaccessible libvirt, or an unexpected VM state can block startup. If only the viewer fails, check the VM state separately with `malware-lab.sh status` and open it manually:

```bash
virt-viewer --connect qemu:///system remnux-lab
```

The absence of a virtual NIC prevents ordinary guest network access, but no VM guarantees perfect containment.

## `import FILE` — attach read-only transfer media

```bash
malware-lab.sh import /absolute/path/to/file.zip
```

**Before:** The VM must be **shut off**, pass the isolation checks, and have a validated `clean-spice` snapshot. The input must be a readable regular file (not a symlink). The host needs `xorriso`, `restorecon`, `realpath`, and `virt-xml`.

**Result:** Builds an ISO9660 image of the input **without extracting or running it on the host**, saves that ISO inside the VM directory's `imports/` area, and attaches it to `remnux-lab` as a read-only virtual CD-ROM. The original file is not changed. The command changes the VM's persistent virtual-media configuration and creates host-side files; a later `reset` does **not** delete those host-side files.

Typical ending:

```text
Read-only ISO attached to the powered-off VM.
Start REMnux with: malware-lab.sh start
```

After `start`, the guest may auto-mount the media at `/media/remnux/MALWARE_LAB`. Verify the actual mount point from inside REMnux:

```bash
lsblk
ls /media/remnux/MALWARE_LAB
```

**If it fails:** Shut the VM down and verify `sudo virsh domstate remnux-lab`, check the input path, free space, SELinux labeling, and `clean-spice`. Do not enable shared folders or networking as a workaround.

## `reset` — discard guest changes and restore baseline

```bash
malware-lab.sh reset
```

**Before:** `clean-spice` must exist and pass its saved-configuration checks; the current VM definition must pass isolation too. Use an interactive terminal. **Save any guest-only investigation results that you intend to keep first.**

**Result:** Shows a warning and requires the exact confirmation:

```text
RESET remnux-lab
```

After confirmation, the CLI checks isolation and snapshot metadata again. If the VM is running, it **force-powers it off** (like `virsh destroy`, not deletion), then reverts only `remnux-lab` to `clean-spice`. This can cause data loss inside the guest. It does not delete the VM, affect other VMs, or remove original files and ISO images from the host's `imports/` directory.

**If it fails:** Missing/unsafe snapshot, noninteractive use, incorrect confirmation, or unsafe VM configuration prevents reset. Do not repeatedly run it without investigating the error.

## `harden` — remove one recognized guest channel

```bash
malware-lab.sh harden
```

**Before:** `remnux-lab` must be shut off and its saved configuration must contain **exactly one** supported channel: a recognized QEMU guest-agent or SPICE/vdagent channel. Run interactively.

**Result:** Identifies that channel, explains the change, and requires the exact confirmation:

```text
HARDEN remnux-lab
```

On confirmation, saves the original domain XML under the VM directory's `config-backups/` folder, then removes the channel from the **persistent definition only**. Does not touch snapshots, disks, or other VMs.

**If it fails:** Zero channels, multiple channels, or an unrecognized channel are refused. This command does **not** remove USB-redirection devices: inspect such devices separately before starting. A legacy snapshot may also restore the old configuration, so use the verified `clean-spice` recovery point.

## Example: harmless end-to-end check

Run these commands on the host while the VM is shut off:

```bash
malware-lab.sh doctor
printf 'REMnux lab transfer test\n' > lab-test.txt
malware-lab.sh import "$PWD/lab-test.txt"
malware-lab.sh start
```

Inside REMnux, inspect the mounted test file:

```bash
ls /media/remnux/MALWARE_LAB
cat /media/remnux/MALWARE_LAB/lab-test.txt
```

When finished, power off the guest with `sudo poweroff`. Use `malware-lab.sh reset` **only if you intend to discard subsequent guest changes**; the host-side transfer ISO remains until intentionally managed outside the CLI.

## Troubleshooting essentials

| Symptom | Suggested first check |
| --- | --- |
| `Cannot access VM 'remnux-lab'` | `sudo virsh -c qemu:///system dominfo remnux-lab`; verify system libvirt |
| Missing `virtstoraged-sock` | `sudo systemctl status virtstoraged.socket` |
| `SAFETY CHECK FAILED` | Inspect `sudo virsh dumpxml --inactive remnux-lab`; review unexpected devices |
| `clean-spice MISSING` | Create a clean, shut-off SPICE/QXL snapshot only after inspecting guest and detaching transfer media |
| `Import requires remnux-lab shut off` | Power off from inside the guest, then verify `sudo virsh domstate remnux-lab` |
| Viewer opens but no desktop | Inspect guest display/logs; keep networking/sharing disabled |
| Host/guest clipboard doesn't work | Expected: no clipboard channel is configured by design |
| `Harden requires an interactive terminal` or `Reset requires an interactive terminal` | Run directly in an interactive terminal; never automate confirmations |

For initial provisioning, see [Usage and recovery](usage.md). For limitations and threat boundaries, see [Security model](security.md). **Offline isolation reduces risk; it does not guarantee containment against VM escapes or host vulnerabilities.**
