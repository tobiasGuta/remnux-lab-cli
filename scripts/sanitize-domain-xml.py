#!/usr/bin/env python3
"""Fail-closed sanitization of a newly generated REMnux domain XML.

Reads virt-install --print-xml from stdin and emits domain XML suitable for
`virsh define` only after removing known auto-generated SPICE sharing devices.
This never connects to libvirt or modifies a virtual machine.
"""
import os
import sys
import xml.etree.ElementTree as ET


def fatal(message):
    print(f"Refusing new VM definition: {message}", file=sys.stderr)
    raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        fatal("usage: sanitize-domain-xml.py /absolute/path/to/remnux-noble-amd64.qcow2")
    expected = sys.argv[1]
    if not os.path.isabs(expected) or os.path.basename(expected) != "remnux-noble-amd64.qcow2":
        fatal("unexpected disk path")
    try:
        root = ET.parse(sys.stdin).getroot()
    except ET.ParseError as exc:
        fatal(f"invalid generated domain XML: {exc}")
    if root.tag != "domain" or root.findtext("name") != "remnux-lab":
        fatal("unexpected domain identity")
    devices = root.find("devices")
    if devices is None:
        fatal("missing devices")

    disks = devices.findall("disk")
    if len(disks) != 1 or disks[0].get("device", "disk") != "disk":
        fatal("expected exactly one primary disk and no extra storage")
    source = disks[0].find("source")
    driver = disks[0].find("driver")
    if (source is None or source.get("file") != expected or driver is None
            or driver.get("type") != "qcow2" or disks[0].find("readonly") is not None):
        fatal("primary disk path or format not approved")

    graphics = devices.findall("graphics")
    video = devices.findall("video")
    if len(graphics) != 1 or graphics[0].get("type") != "spice":
        fatal("expected one SPICE graphics device")
    if graphics[0].get("listen") != "127.0.0.1":
        fatal("SPICE must listen only on 127.0.0.1")
    for listen in graphics[0].findall("listen"):
        if listen.get("address") not in (None, "127.0.0.1"):
            fatal("SPICE has an unexpected secondary listener")
    if len(video) != 1 or video[0].find("model") is None or video[0].find("model").get("type") != "qxl":
        fatal("expected one QXL video device")

    for name in ("interface", "filesystem", "hostdev", "smartcard", "shmem", "vsock", "tpm"):
        if devices.findall(name):
            fatal(f"unexpected device: {name}")
    for channel in devices.findall("channel"):
        target = channel.find("target")
        kind = channel.get("type")
        target_name = target.get("name") if target is not None else None
        target_type = target.get("type") if target is not None else None
        if not ((kind == "spicevmc" and target_name == "com.redhat.spice.0" and target_type == "virtio")
                or (kind == "unix" and target_name == "org.qemu.guest_agent.0" and target_type == "virtio")):
            fatal("unknown host-guest channel; refusing automatic removal")
        devices.remove(channel)
    for redir in devices.findall("redirdev"):
        if redir.get("bus") != "usb" or redir.get("type") != "spicevmc":
            fatal("unknown redirection device; refusing automatic removal")
        devices.remove(redir)

    if devices.findall("channel") or devices.findall("redirdev"):
        fatal("host integration devices still present")
    ET.indent(root, space="  ")
    sys.stdout.write(ET.tostring(root, encoding="unicode", xml_declaration=False) + "\n")


if __name__ == "__main__":
    main()
