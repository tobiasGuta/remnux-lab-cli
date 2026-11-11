#!/usr/bin/env python3
"""Fail-closed domain/snapshot regression tests; all libvirt commands are mocked."""
import concurrent.futures
import tempfile
from channel_policy import fake_lab, run

CASES = {
    'network': ('<interface type="network"><source network="default"/></interface>', 'unexpected device: interface'),
    'shared folder': ('<filesystem type="mount"><source dir="/home"/><target dir="home"/></filesystem>', 'unexpected device: filesystem'),
    'PCI passthrough': ('<hostdev mode="subsystem" type="pci"/>', 'unexpected device: hostdev'),
    'USB passthrough': ('<hostdev mode="subsystem" type="usb"/>', 'unexpected device: hostdev'),
    'vsock': ('<vsock model="virtio"/>', 'unexpected device: vsock'),
    'agent channel': ('<channel type="unix"><target type="virtio" name="org.qemu.guest_agent.0"/></channel>', 'host-guest channel'),
    'public VNC': ('<graphics type="vnc" listen="0.0.0.0"/>', 'graphics does not listen only on loopback'),
    'extra disk': ('<disk type="file" device="disk"><driver name="qemu" type="qcow2"/><source file="/tmp/external.qcow2"/></disk>', 'unexpected primary disk'),
}


def trial(task):
    label, xml, reason, source = task
    with tempfile.TemporaryDirectory() as base:
        env, write_xml, lab, write_snapshot = fake_lab(base)
        write_xml('')
        if source == 'persistent':
            write_xml(xml)
            cmd = 'status'
        else:
            write_snapshot(xml)
            cmd = 'reset'
        r = run(env, cmd)
        good = reason in r.stderr or (label == 'extra disk' and source == 'persistent' and 'Unexpected or missing REMnux disk path' in r.stderr)
        assert r.returncode != 0 and good, f'{label}/{source}: {r.stderr}'
        return f'{source}: {label}'


def snapshots_edge_cases():
    with tempfile.TemporaryDirectory() as base:
        env, write_xml, lab, write_snapshot = fake_lab(base)
        write_xml('')
        for kwargs, error in [
            ({'state': 'running'}, 'not from a shut-off guest'),
            ({'domain': False}, 'lacks embedded domain configuration'),
        ]:
            write_snapshot(**kwargs)
            r = run(env, 'reset')
            assert r.returncode != 0 and error in r.stderr, r.stderr
        write_snapshot()
        r = run(env, 'status')
        assert r.returncode == 0 and 'clean-hardened present' in r.stdout, r.stderr
        r = run(env, 'reset')
        assert r.returncode != 0 and 'interactive terminal' in r.stderr, r.stderr
        return 'snapshot structure, safe status and noninteractive reset'


def test():
    tasks = [(name, xml, reason, source) for name, (xml, reason) in CASES.items() for source in ('persistent', 'snapshot')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(trial, tasks))
        results.append(snapshots_edge_cases())
    print(f'Security policy: {len(results)} mock scenarios passed; no real VMs touched.')


if __name__ == '__main__':
    test()
