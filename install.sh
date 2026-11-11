#!/usr/bin/env bash
# Install only the CLI; it does not create or modify virtual machines.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "$ROOT/scripts/malware-lab.sh" ]] || { echo 'Missing scripts/malware-lab.sh' >&2; exit 1; }
sudo install -m 0755 "$ROOT/scripts/malware-lab.sh" /usr/local/bin/malware-lab.sh
printf 'Installed /usr/local/bin/malware-lab.sh\nTry: malware-lab.sh status\n'
