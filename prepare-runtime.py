#!/usr/bin/env python3
"""Restore mounts for this Pi's existing RX3 rootfs; never assemble/replace it.

Run as pompu_5. --check only inspects. Mount operations use sudo -n.
The original USB export remains read-only; local USB2 database/analysis persist.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path('/home/pompu_5/rx3-rootfs')
USB_UUID = '0FFF-3865'


def command(*args):
    subprocess.run(args, check=True)


def mounted(path):
    return subprocess.run(['mountpoint', '-q', str(path)]).returncode == 0


def same(source, target):
    try:
        return os.path.samefile(source, target)
    except FileNotFoundError:
        return False


def bind(source, target, readonly, check, errors):
    source, target = Path(source), Path(target)
    if not source.exists():
        errors.append(f'Missing source: {source}')
        return
    if mounted(target):
        if not same(source, target):
            errors.append(f'Unexpected mount at {target}; left unchanged')
            return
    elif check:
        errors.append(f'Missing bind mount: {target}')
        return
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            target.mkdir(exist_ok=True)
        elif not target.exists():
            target.touch()
        command('sudo', '-n', 'mount', '--bind', str(source), str(target))
    if readonly:
        options = subprocess.check_output(['findmnt', '-n', '-o', 'OPTIONS', '-M', str(target)], text=True).strip().split(',')
        if 'ro' not in options:
            if check:
                errors.append(f'Mount is not read-only: {target}')
            else:
                command('sudo', '-n', 'mount', '-o', 'remount,bind,ro', str(target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Inspect without changing mounts or files')
    args = parser.parse_args()
    errors = []
    for name in ['root/pdj/rbp-pi', 'lib/fbshim.so', 'bin/busybox', 'etc/asound.conf']:
        if not (ROOT / name).is_file():
            errors.append(f'Missing existing runtime file: {ROOT / name}')
    if errors:
        raise SystemExit('\n'.join(errors))
    for name in ['null', 'zero', 'urandom', 'full', 'snd']:
        bind(Path('/dev') / name, ROOT / 'dev' / name, False, args.check, errors)
    # Preserve the firmware-specific fake /proc files; mount only ALSA's subtree.
    bind('/proc/asound', ROOT / 'proc/asound', False, args.check, errors)
    usb = ROOT / 'media/usb1/sda1'
    device = Path('/dev/disk/by-uuid') / USB_UUID
    if mounted(usb):
        actual = subprocess.check_output(['findmnt', '-n', '-o', 'UUID', '-M', str(usb)], text=True).strip()
        if actual != USB_UUID:
            errors.append(f'Unexpected USB filesystem at {usb}; left unchanged')
            device = None
        else:
            options = subprocess.check_output(['findmnt', '-n', '-o', 'OPTIONS', '-M', str(usb)], text=True).strip().split(',')
            if 'ro' not in options:
                errors.append(f'USB1 is not read-only: {usb}; left unchanged')
                device = None
    elif device.exists():
        if args.check:
            errors.append(f'Missing USB1 mount: {usb}')
            device = None
        else:
            existing = subprocess.run(['findmnt', '-J', '-o', 'TARGET,FSROOT,OPTIONS', '-S', 'UUID=' + USB_UUID], capture_output=True, text=True)
            roots = json.loads(existing.stdout).get('filesystems', []) if existing.returncode == 0 else []
            roots = [r for r in roots if r.get('fsroot') == '/' and not Path(r['target']).is_relative_to(ROOT)]
            if roots:
                host = roots[0]
                options = host['options'].split(',')
                if not any(v in options for v in ('utf8', 'utf8=1')):
                    errors.append('Existing USB mount needs UTF-8 filenames; left unchanged')
                    device = None
                else:
                    bind(host['target'], usb, True, False, errors)
            else:
                usb.mkdir(parents=True, exist_ok=True)
                command('sudo', '-n', 'mount', '-t', 'vfat', '-o', 'ro,uid=1000,gid=1000,utf8=1,nosuid,nodev,noexec', str(device), str(usb))
    else:
        print(f'USB {USB_UUID} absent; player can start without media.')
        device = None
    if device is not None and mounted(usb):
        for part in ['Contents', 'Music', 'PIONEER/Artwork']:
            if (usb / part).is_dir():
                bind(usb / part, ROOT / 'media/usb2/sdb1' / part, True, args.check, errors)
        for part in ['PIONEER/rekordbox', 'PIONEER/USBANLZ']:
            if not (ROOT / 'media/usb2/sdb1' / part).is_dir():
                errors.append(f'Missing prepared local library: {part}; run prepare-library-view.sh')
    if errors:
        raise SystemExit('\n'.join(errors))
    print('RX3 runtime mounts ready; local library files preserved.')


if __name__ == '__main__':
    main()
