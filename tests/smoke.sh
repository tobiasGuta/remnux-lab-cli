#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for file in "$ROOT/install.sh" "$ROOT/scripts/setup-remnux-lab.sh" "$ROOT/scripts/malware-lab.sh"; do
  bash -n "$file"
done
"$ROOT/scripts/setup-remnux-lab.sh" --help | grep -q 'storage-dir'
"$ROOT/scripts/malware-lab.sh" --help | grep -q 'clean-hardened'
# A misuse must be rejected without touching any VM.
if "$ROOT/scripts/malware-lab.sh" no-such-command >/dev/null 2>&1; then
  echo 'Unknown subcommand should fail' >&2
  exit 1
fi
if "$ROOT/scripts/setup-remnux-lab.sh" --memory 4096 >/dev/null 2>&1; then
  echo 'Missing storage path should fail' >&2
  exit 1
fi
# Protect against scope creeping to guest networking or unrelated domain deletion.
! grep -Eq 'virsh_lab (undefine|vol-delete|pool-destroy)' "$ROOT/scripts/malware-lab.sh"
grep -Fq -- '--network none' "$ROOT/scripts/setup-remnux-lab.sh"
grep -Fq -- 'host-guest channel:' "$ROOT/scripts/malware-lab.sh"
grep -Fq -- 'HARDEN $VM' "$ROOT/scripts/malware-lab.sh"
printf 'Smoke tests passed. No VM was created or modified.\n'
