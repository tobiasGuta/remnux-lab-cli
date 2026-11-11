#!/usr/bin/env python3
"""Read-only CLI diagnostics and snapshot tests; mocks, no real libvirt access."""
from pathlib import Path
import tempfile
from channel_policy import fake_lab, run


def test():
    with tempfile.TemporaryDirectory() as base:
        env, write_xml, _lab, write_snapshot = fake_lab(base)
        write_xml('')
        log = Path(base) / 'commands.log'
        env['MOCK_VIRSH_LOG'] = str(log)
        virsh = Path(base) / 'mock-bin' / 'virsh'
        current = virsh.read_text()
        current = current.replace(
            'case "$1" in',
            'if [ -n "${MOCK_VIRSH_LOG:-}" ]; then printf "%s\\n" "$*" >> "$MOCK_VIRSH_LOG"; fi\ncase "$1" in',
        )
        virsh.write_text(current)

        r = run(env, 'snapshots')
        assert r.returncode == 0, r.stderr
        assert 'clean-hardened' in r.stdout and 'clean-base' in r.stdout, r.stdout
        assert 'Verified reset target: clean-hardened' in r.stdout
        assert 'NEVER be used by reset' in r.stdout

        r = run(env, 'doctor')
        assert 'Diagnostic summary:' in r.stdout, (r.stdout, r.stderr)
        assert '[PASS] Saved VM configuration' in r.stdout, (r.stdout, r.stderr)
        assert '[PASS] Recovery snapshot clean-hardened' in r.stdout, (r.stdout, r.stderr)
        assert '[PASS] Lab filesystem' in r.stdout or '[WARN] Lab filesystem' in r.stdout
        # /dev/kvm may be absent on CI, which is an expected diagnostic failure.
        assert r.returncode in (0, 1)

        unsafe = '<interface type="network"><source network="default"/></interface>'
        write_xml(unsafe)
        r = run(env, 'doctor')
        assert r.returncode != 0 and 'Saved VM configuration violates isolation' in r.stdout, (r.stdout, r.stderr)
        write_xml('')
        write_snapshot(unsafe)
        r = run(env, 'snapshots')
        assert r.returncode != 0 and 'unexpected device: interface' in r.stderr, r.stderr
        r = run(env, 'doctor')
        assert r.returncode != 0 and 'Recovery snapshot clean-hardened is unsafe' in r.stdout, (r.stdout, r.stderr)

        commands = log.read_text().splitlines()
        allowed = {'dominfo', 'dumpxml', 'domstate', 'snapshot-list', 'snapshot-dumpxml'}
        unexpected = [x for x in commands if x.split()[0] not in allowed]
        assert not unexpected, f'Read-only commands called mutating virsh operations: {unexpected}'
        print('Diagnostics policy: read-only doctor/snapshots, safe baseline and unsafe-config rejection passed.')


if __name__ == '__main__':
    test()
