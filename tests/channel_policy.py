#!/usr/bin/env python3
"""Libvirt XML regression checks against mock commands; touches no real VMs."""
import os
import pathlib
import pty
import select
import subprocess
import tempfile
import time

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / 'scripts/malware-lab.sh'


def fake_lab(base):
    base = pathlib.Path(base)
    lab = base / 'remnux-lab'
    lab.mkdir()
    disk = lab / 'remnux-noble-amd64.qcow2'
    disk.write_bytes(b'mock disk, not a real image')
    bin_dir = base / 'mock-bin'
    bin_dir.mkdir()
    sudo = bin_dir / 'sudo'
    sudo.write_text('#!/bin/sh\nexec "$@"\n')
    sudo.chmod(0o755)
    virsh = bin_dir / 'virsh'
    virsh.write_text('''#!/bin/sh
set -eu
[ "$1" = '-c' ] && shift 2
case "$1" in
  dominfo) echo 'Id: -' ;;
  dumpxml) cat "$MOCK_XML" ;;
  domstate) echo 'shut off' ;;
  snapshot-list) printf 'clean-base\nclean-hardened\nclean-spice\n' ;;
  snapshot-dumpxml) cat "$MOCK_SNAPSHOT_XML" ;;
  domiflist) printf ' Interface   Type   Source   Model   MAC\\n-----\\n' ;;
  domblklist) printf ' Type   Device   Target   Source\\n-----\\n' ;;
  detach-device)
    grep -q 'org.qemu.guest_agent.0' "$3" || exit 9
    sed -i '/<channel type="unix">/d' "$MOCK_XML"
    echo 'Device detached successfully' ;;
  *) echo "Unexpected mock virsh args: $*" >&2; exit 99 ;;
esac
''')
    virsh.chmod(0o755)
    xml = base / 'domain.xml'
    snapshot = base / 'snapshot.xml'
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'], MOCK_XML=str(xml), MOCK_SNAPSHOT_XML=str(snapshot))

    def write_xml(channel):
        xml.write_text(f'''<domain type="kvm"><name>remnux-lab</name><devices>
<disk type="file" device="disk"><driver name="qemu" type="qcow2"/><source file="{disk}"/><target dev="sda" bus="scsi"/></disk>
<graphics type="spice" listen="127.0.0.1"/><video><model type="qxl"/></video>
{channel}
</devices></domain>''')
    def write_snapshot(device='', state='shutoff', domain=True):
        domain_xml = f'''<domain type="kvm"><name>remnux-lab</name><devices>
<disk type="file" device="disk"><driver name="qemu" type="qcow2"/><source file="{disk}"/><target dev="sda" bus="scsi"/></disk>
<graphics type="spice" listen="127.0.0.1"/><video><model type="qxl"/></video>
{device}
</devices></domain>''' if domain else ''
        snapshot.write_text(f'<domainsnapshot><name>clean-spice</name><state>{state}</state>{domain_xml}</domainsnapshot>')

    write_snapshot()
    return env, write_xml, lab, write_snapshot


def run(env, action):
    return subprocess.run(['bash', str(SCRIPT), action], env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=45)


def test():
    agent = '<channel type="unix"><target type="virtio" name="org.qemu.guest_agent.0"/></channel>'
    unusual = '<channel type="tcp"><target type="virtio" name="unknown-channel"/></channel>'
    with tempfile.TemporaryDirectory() as base:
        env, write_xml, lab, write_snapshot = fake_lab(base)
        write_xml(agent)
        r = run(env, 'status')
        assert r.returncode != 0 and 'host-guest channel: type=unix target=org.qemu.guest_agent.0' in r.stderr, r.stderr
        r = run(env, 'harden')
        assert r.returncode != 0 and 'interactive terminal' in r.stderr, r.stderr
        write_xml(unusual)
        r = run(env, 'harden')
        assert r.returncode != 0 and 'Unrecognized host-guest channel' in r.stderr, r.stderr
        write_xml(agent)
        master, slave = pty.openpty()
        proc = subprocess.Popen(['bash', str(SCRIPT), 'harden'], stdin=slave, stdout=slave, stderr=slave, env=env)
        os.close(slave)
        output = b''
        confirmed = False
        end = time.monotonic() + 15
        while time.monotonic() < end:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try:
                    chunk = os.read(master, 32768)
                except OSError:
                    break
                if not chunk:
                    break
                output += chunk
                if b'Type exactly HARDEN remnux-lab to continue:' in output and not confirmed:
                    os.write(master, b'HARDEN remnux-lab\n')
                    confirmed = True
            if proc.poll() is not None:
                break
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        os.close(master)
        assert confirmed and proc.returncode == 0, output.decode(errors='replace')
        assert 'Channel removed from remnux-lab' in output.decode(errors='replace')
        assert list((lab / 'config-backups').glob('remnux-lab-before-harden-*.xml'))
        assert run(env, 'status').returncode == 0
        print('Channel policy: standard channel rejected, unknown refused, confirmed harden works, channel-free status passes.')


if __name__ == '__main__':
    test()
