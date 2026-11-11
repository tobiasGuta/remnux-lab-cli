#!/usr/bin/env python3
"""Tests safe SPICE/QXL XML provisioning without libvirt or any real VM."""
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/sanitize-domain-xml.py'
DISK = '/mnt/virtual/remnux-lab/remnux-noble-amd64.qcow2'

BASE = '''<domain type="kvm"><name>remnux-lab</name><devices>
<disk type="file" device="disk"><driver name="qemu" type="qcow2"/><source file="{disk}"/></disk>
<graphics type="spice" listen="127.0.0.1"><listen type="address" address="127.0.0.1"/></graphics>
<video><model type="qxl"/></video>
{extra}</devices></domain>'''
AGENT = '<channel type="spicevmc"><target type="virtio" name="com.redhat.spice.0"/></channel>'
REDIR = '<redirdev bus="usb" type="spicevmc"/>'


def sanitize(xml):
    return subprocess.run([sys.executable, str(SCRIPT), DISK], input=xml, text=True, capture_output=True, timeout=8)


def test():
    safe = BASE.format(disk=DISK, extra=AGENT + REDIR + REDIR)
    r = sanitize(safe)
    assert r.returncode == 0, r.stderr
    root = ET.fromstring(r.stdout)
    assert root.find('./devices/graphics').get('type') == 'spice'
    assert root.find('./devices/video/model').get('type') == 'qxl'
    assert not root.findall('./devices/channel') and not root.findall('./devices/redirdev')

    r = sanitize(BASE.format(disk=DISK, extra=''))
    assert r.returncode == 0, r.stderr

    cases = {
        'unknown channel': ('<channel type="tcp"><target name="other"/></channel>', 'unknown host-guest channel'),
        'unknown redirection': ('<redirdev bus="usb" type="tcp"/>', 'unknown redirection device'),
        'network': ('<interface type="network"/>', 'unexpected device: interface'),
        'host shared filesystem': ('<filesystem type="mount"/>', 'unexpected device: filesystem'),
        'device passthrough': ('<hostdev type="pci"/>', 'unexpected device: hostdev'),
        'vsock': ('<vsock model="virtio"/>', 'unexpected device: vsock'),
        'extra disk': (f'<disk type="file" device="disk"><driver type="qcow2"/><source file="{DISK}"/></disk>', 'one primary disk'),
    }
    for label, (extra, message) in cases.items():
        r = sanitize(BASE.format(disk=DISK, extra=extra))
        assert r.returncode != 0 and message in r.stderr, (label, r.stderr)
    for label, altered, message in [
        ('public SPICE', safe.replace('listen="127.0.0.1"', 'listen="0.0.0.0"'), 'SPICE must listen'),
        ('VNC graphics', safe.replace('type="spice"', 'type="vnc"'), 'SPICE graphics'),
        ('VGA video', safe.replace('type="qxl"', 'type="vga"'), 'QXL video'),
        ('wrong VM', safe.replace('<name>remnux-lab</name>', '<name>unrelated</name>'), 'domain identity'),
        ('wrong disk', safe.replace(DISK, '/home/user/test.img'), 'primary disk path'),
    ]:
        r = sanitize(altered)
        assert r.returncode != 0 and message in r.stderr, (label, r.stderr)
    print('Provisioning policy: safe SPICE/QXL XML sanitized; 12 unsafe cases rejected, no VMs touched.')


if __name__ == '__main__':
    test()
