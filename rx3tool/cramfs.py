"""Read the firmware's cramfs root filesystem without root or loop devices.

The image is memory-mapped and each file is decompressed one 4 KiB block at a
time. Names, offsets and directory structure are validated, so a damaged image
fails with a clear message instead of writing outside the destination.
"""
import mmap
import stat
import struct
import zlib
from pathlib import PurePosixPath

from .ui import Failure

MAGIC = 0x28cd3d45
BLOCK = 4096
# Version-2 fsid, sorted directories, holes, wrong signature. Extended block
# pointers (0x800) and a shifted root (0x400) are not used by the RX3 image.
SUPPORTED_FLAGS = 0x1 | 0x2 | 0x100 | 0x200
MAX_DEPTH = 64


class Image:
    def __init__(self, path):
        self.path = path
        self.handle = open(path, 'rb')
        try:
            self.data = mmap.mmap(self.handle.fileno(), 0, access=mmap.ACCESS_READ)
        except ValueError:
            self.handle.close()
            raise Failure(f'{path} is empty, not a cramfs image')
        if len(self.data) < 76:
            self.close()
            raise Failure(f'{path} is too small to be a cramfs image')
        magic, length, flags = struct.unpack_from('<III', self.data)
        if magic != MAGIC:
            self.close()
            raise Failure(f'{path} is not a cramfs image')
        if flags & ~SUPPORTED_FLAGS:
            self.close()
            raise Failure(f'{path} uses unsupported cramfs features (flags {flags:#x})')
        if length > len(self.data):
            actual = len(self.data)
            self.close()
            raise Failure(f'{path} is truncated ({actual} of {length} bytes)')

    def close(self):
        if getattr(self, 'data', None) is not None:
            self.data.close()
            self.data = None
        self.handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def inode(self, pos):
        if pos + 12 > len(self.data):
            raise Failure('cramfs inode outside the image')
        a, b, c = struct.unpack_from('<III', self.data, pos)
        return a & 0xffff, b & 0xffffff, (c & 63) * 4, (c >> 6) * 4

    def blocks(self, size, offset):
        """Yield the decompressed contents of a regular file or symlink."""
        count = (size + BLOCK - 1) // BLOCK
        if offset + count * 4 > len(self.data):
            raise Failure('cramfs block table outside the image')
        start = offset + count * 4
        remaining = size
        for index in range(count):
            end = struct.unpack_from('<I', self.data, offset + index * 4)[0]
            if not start <= end <= len(self.data):
                raise Failure('cramfs block pointer outside the image')
            if end == start:
                block = bytes(BLOCK)
            else:
                decompressor = zlib.decompressobj()
                block = decompressor.decompress(self.data[start:end], BLOCK + 1)
                if len(block) > BLOCK:
                    raise Failure('cramfs block larger than 4 KiB')
            want = min(BLOCK, remaining)
            if len(block) < want:
                raise Failure('cramfs block shorter than expected')
            yield block[:want]
            remaining -= want
            start = end

    def read(self, size, offset):
        return b''.join(self.blocks(size, offset))

    def walk(self):
        """Yield (kind, path, mode, size, offset) depth-first, parents first."""
        visited = set()

        def directory(pos, path, depth):
            mode, size, _, offset = self.inode(pos)
            if depth > MAX_DEPTH:
                raise Failure('cramfs directory tree is too deep')
            if size and offset in visited:
                raise Failure('cramfs directory loop')
            visited.add(offset)
            entry = offset
            while entry < offset + size:
                child_mode, child_size, name_len, child_offset = self.inode(entry)
                raw = bytes(self.data[entry + 12:entry + 12 + name_len]).rstrip(b'\0')
                try:
                    name = raw.decode('utf-8')
                except UnicodeDecodeError:
                    raise Failure('cramfs contains a file name that is not UTF-8')
                if not name or name in ('.', '..') or '/' in name or '\0' in name:
                    raise Failure(f'cramfs contains an unsafe name: {raw!r}')
                child = path / name
                if stat.S_ISDIR(child_mode):
                    yield 'dir', child, child_mode, child_size, child_offset
                    yield from directory(entry, child, depth + 1)
                elif stat.S_ISREG(child_mode):
                    yield 'file', child, child_mode, child_size, child_offset
                elif stat.S_ISLNK(child_mode):
                    yield 'symlink', child, child_mode, child_size, child_offset
                else:
                    yield 'special', child, child_mode, child_size, child_offset
                if name_len == 0:
                    raise Failure('cramfs directory entry without a name')
                entry += 12 + name_len

        root_mode = self.inode(64)[0]
        if not stat.S_ISDIR(root_mode):
            raise Failure('cramfs root is not a directory')
        yield from directory(64, PurePosixPath(), 0)


class BlockReader:
    """File-like adapter so safefs.Tree.write can stream a cramfs file."""

    def __init__(self, blocks):
        self.blocks = blocks
        self.pending = b''

    def read(self, size=-1):
        while size < 0 or len(self.pending) < size:
            try:
                self.pending += next(self.blocks)
            except StopIteration:
                break
        if size < 0:
            data, self.pending = self.pending, b''
        else:
            data, self.pending = self.pending[:size], self.pending[size:]
        return data


def extract(image_path, tree, replace=False):
    """Write every directory, regular file and symlink of the image into `tree`.

    Device nodes, FIFOs and sockets are counted but not created; the runtime
    provides its own emulated files instead. Returns statistics and the
    recorded symlinks.
    """
    stats = {'dirs': 0, 'files': 0, 'symlinks': 0, 'special': 0, 'unchanged': 0}
    links = {}
    with Image(image_path) as image:
        for kind, path, mode, size, offset in image.walk():
            relative = str(path)
            if kind == 'dir':
                tree.mkdir(relative, (mode & 0o777) | 0o700)
                stats['dirs'] += 1
            elif kind == 'file':
                existing = tree.lstat(relative)
                if existing is not None and not replace and stat.S_ISREG(existing.st_mode) \
                        and existing.st_size == size:
                    stats['unchanged'] += 1
                    continue
                tree.write(relative, BlockReader(image.blocks(size, offset)), (mode & 0o777) | 0o600)
                stats['files'] += 1
            elif kind == 'symlink':
                target = image.read(size, offset).decode('utf-8', 'strict')
                links[relative] = target
                if tree.symlink(relative, target, replace=replace):
                    stats['symlinks'] += 1
                else:
                    stats['unchanged'] += 1
            else:
                stats['special'] += 1
    return stats, links
