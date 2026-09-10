"""Extract regular files from this firmware's cramfs without root/device nodes."""
import json
import pathlib
import stat
import struct
import zlib

base = pathlib.Path(__file__).resolve().parent
data = (base / 'extracted/update/images/rootfs.cramfs').read_bytes()
target = base / 'extracted/runtime-files'
magic, length, flags = struct.unpack_from('<III', data)
assert magic == 0x28cd3d45 and not flags & 0x800
links = {}
count = 0

def inode(pos):
    a, b, c = struct.unpack_from('<III', data, pos)
    return a & 65535, b & 0xffffff, (c & 63) * 4, (c >> 6) * 4

def contents(size, offset):
    blocks = (size + 4095) // 4096
    start = offset + blocks * 4
    result = bytearray()
    for i in range(blocks):
        end = struct.unpack_from('<I', data, offset + i * 4)[0]
        assert start <= end <= len(data)
        result.extend(zlib.decompress(data[start:end]) if end > start else bytes(4096))
        start = end
    assert len(result) >= size
    return bytes(result[:size])

def walk(pos, path):
    global count
    mode, size, _, offset = inode(pos)
    dest = target / path
    if stat.S_ISDIR(mode):
        dest.mkdir(parents=True, exist_ok=True)
        entry = offset
        while entry < offset + size:
            _, _, nlen, _ = inode(entry)
            name = data[entry+12:entry+12+nlen].rstrip(b'\0').decode()
            assert name not in ('.', '..') and '/' not in name
            walk(entry, path / name)
            entry += 12 + nlen
    elif stat.S_ISREG(mode):
        dest.write_bytes(contents(size, offset))
        dest.chmod(mode & 0o777)
        count += 1
    elif stat.S_ISLNK(mode):
        links[str(path)] = contents(size, offset).decode()

walk(64, pathlib.Path())
(base / 'runtime-symlinks.json').write_text(json.dumps(links, indent=2))
print(f'Extracted {count} regular files; recorded {len(links)} symlinks; skipped device nodes.')
