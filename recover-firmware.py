#!/usr/bin/env python3
"""Recover RX3 1.19 files from official downloads with bounded memory; never flash."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from firmware_image import crypt_stream, load_key, autoexec_iso_metadata

BASE = Path(__file__).resolve().parent
SOURCES = [
    'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/f7f69f5f428841898c6d98f9976c23bb/A9BEE4F7-6932-4E11-8D9F-5288F5F79EC2.zip',
    'https://files.microcms-assets.io/assets/3b9e29ce734e49babfedb3f8d1e728e3/5b39b9d79cc747c2b31ff39e22074bad/57CB205B-D45A-4143-BC09-22D8400074C2.zip',
]
SOURCE_HASHES = {
    '6280e9e2c1c31a2d943608fde753de79c61b08f775aa063805ff84519537f484',
    '0cb9277161e57e35d3fd84823a926ea0ba6a342c07817cf871dc5d286b5b0169',
}
FIRMWARE_URL = 'https://downloads.support.alphatheta.com/firmwares/all-in-one-dj-systems/XDJ-RX3/XDJ-RX3_v119.zip'
FIRMWARE_HASH = 'ccef2b983ff9effed51bbf976d9679d3a1ba967e0474258023c6957e9e608f83'
PLAYER_HASH = '60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09'
BUFFER = 1024 * 1024


def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(BUFFER), b''):
            h.update(block)
    return h.hexdigest()


def download(url, path, hashes):
    if not path.exists():
        print('Downloading', path.name, flush=True)
        partial = path.with_suffix(path.suffix + '.partial')
        urllib.request.urlretrieve(url, partial)
        if sha256_file(partial) not in hashes:
            raise ValueError('Unexpected download hash: ' + str(partial))
        partial.replace(path)
    elif sha256_file(path) not in hashes:
        raise ValueError('Unexpected cached download hash: ' + str(path))
    else:
        print('Using verified download', path.name, flush=True)
    return path


def copy_zip_member(path, name, destination):
    """Stream even ZIP methods unsupported by Python through unzip/7z."""
    with zipfile.ZipFile(path) as archive:
        try:
            source = archive.open(name)
        except NotImplementedError:
            destination.flush()
            if shutil.which('unzip'):
                command = ['unzip', '-p', str(path), name]
            elif shutil.which('7z'):
                command = ['7z', 'x', '-so', str(path), name]
            else:
                raise RuntimeError('Source ZIP compression requires unzip or 7z')
            subprocess.run(command, stdout=destination, check=True)
        else:
            with source:
                shutil.copyfileobj(source, destination, BUFFER)


def recover_key(source_archive, key_path):
    # Both tar layers are sequential streams. Never retain the initramfs in RAM.
    found = []
    with tarfile.open(source_archive, mode='r|bz2') as archive:
        for member in archive:
            if member.name != 'pioneerdj_xdj_rx3/initramfs.tar.gz':
                continue
            with archive.extractfile(member) as initramfs:
                with tarfile.open(fileobj=initramfs, mode='r|gz') as init:
                    for item in init:
                        if item.isfile() and item.name.endswith('/usr/local/pdj/aes256.key'):
                            if item.size > 65536:
                                raise ValueError('Unexpected source key size')
                            with init.extractfile(item) as stream:
                                found.append(stream.read(65537))
            break
    if len(found) != 1:
        raise ValueError('Expected exactly one source-package key')
    key_path.write_bytes(found[0])


def decrypt_update(update, iso, key_path):
    length = update.stat().st_size
    # Observed 1.19 layout only; this is not flash/update authentication.
    if length <= 16 or length % 512 != 16:
        raise ValueError('Unexpected RX3 1.19 update layout')
    partial = iso.with_suffix(iso.suffix + '.partial')
    print('Decrypting firmware to disk (low-memory mode)', flush=True)
    with update.open('rb') as source, partial.open('wb') as target:
        crypt_stream(source, target, length - 16, load_key(key_path), True)
    with partial.open('rb') as source:
        volume = autoexec_iso_metadata(source.read(64 * 512 + 2048))
    partial.replace(iso)
    print('Decrypted ISO volume:', volume, flush=True)


def extract_regular_files(archive_path, destination):
    with tarfile.open(archive_path, mode='r|gz') as archive:
        for member in archive:
            if not member.isfile():
                continue
            path = destination / member.name
            if not path.resolve().is_relative_to(destination.resolve()):
                raise ValueError('Unsafe archive path')
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, path.open('wb') as target:
                shutil.copyfileobj(source, target, BUFFER)
            path.chmod(member.mode & 0o777)


def main():
    out = BASE / 'extracted'
    out.mkdir(exist_ok=True)
    parts = {}
    for i, url in enumerate(SOURCES):
        path = download(url, BASE / f'official-source-{i}.zip', SOURCE_HASHES)
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                leaf = Path(name).name
                if leaf in ('pioneerdj_xdj_rx3.tar.bz2.00', 'pioneerdj_xdj_rx3.tar.bz2.01'):
                    if leaf in parts:
                        raise ValueError('Duplicate source archive part')
                    parts[leaf] = (path, name)
    if len(parts) != 2:
        raise ValueError('Missing source archive part')
    archive_path = out / 'rx3.tar.bz2'
    partial = archive_path.with_suffix(archive_path.suffix + '.partial')
    print('Joining source archive parts on disk', flush=True)
    with partial.open('wb') as target:
        for name in sorted(parts):
            copy_zip_member(*parts[name], target)
    partial.replace(archive_path)
    key_path = BASE / 'aes256.key'
    recover_key(archive_path, key_path)
    print('Recovered source-package firmware key; no device-specific key needed.', flush=True)
    firmware = download(FIRMWARE_URL, BASE / 'XDJ-RX3_v119.zip', {FIRMWARE_HASH})
    with zipfile.ZipFile(firmware) as archive:
        names = [n for n in archive.namelist() if Path(n).name == 'XDJRX3.UPD']
    if len(names) != 1:
        raise ValueError('Expected exactly one firmware update')
    update = out / 'XDJRX3.UPD'
    partial = update.with_suffix('.UPD.partial')
    print('Extracting firmware update to disk', flush=True)
    with partial.open('wb') as target:
        copy_zip_member(firmware, names[0], target)
    partial.replace(update)
    iso = out / 'XDJRX3.iso'
    decrypt_update(update, iso, key_path)
    (out / 'update').mkdir(exist_ok=True)
    if shutil.which('7z'):
        subprocess.run(['7z', 'x', '-y', '-o' + str(out / 'update'), str(iso)], check=True)
    elif shutil.which('bsdtar'):
        subprocess.run(['bsdtar', '-xf', str(iso), '-C', str(out / 'update')], check=True)
    else:
        raise RuntimeError('Install 7z or bsdtar for ISO extraction')
    for name, folder in [('pdj.tar.gz', 'player'), ('gui.tar.gz', 'gui')]:
        extract_regular_files(out / 'update/images' / name, out / folder)
    rbp = out / 'player/pdj/rbp'
    if sha256_file(rbp) != PLAYER_HASH:
        raise ValueError('Unexpected recovered player hash')
    print('Verified original player:', rbp, flush=True)
    print('Next: python3 extract_cramfs.py; read ASTRA-PROMPT.md before deployment.')


if __name__ == '__main__':
    main()
