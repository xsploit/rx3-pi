"""Check that 32-bit ARM programs in the runtime find all their libraries.

This reads ELF headers directly and resolves names the way the runtime's
loader would inside the chroot (/lib, /usr/lib, symlinks relative to the
runtime root), so it works on any computer and never executes the firmware.
"""
import os
import posixpath
import struct

SEARCH = ('/lib', '/usr/lib')
PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
DT_NEEDED, DT_STRTAB = 1, 5


class ElfError(Exception):
    pass


def read_elf32(path):
    """Return (interpreter, [needed names]) of a little-endian ELF32 file."""
    with open(path, 'rb') as handle:
        data = handle.read()
    if len(data) < 52 or data[:7] != b'\x7fELF\x01\x01\x01':
        raise ElfError('not a 32-bit little-endian ELF file')
    phoff = struct.unpack_from('<I', data, 28)[0]
    entsize, count = struct.unpack_from('<HH', data, 42)
    loads, dynamic, interp = [], None, None
    for index in range(count):
        base = phoff + index * entsize
        if base + 32 > len(data):
            raise ElfError('truncated program header')
        kind, offset, vaddr, _, filesz, _, _, _ = struct.unpack_from('<8I', data, base)
        if kind == PT_LOAD:
            loads.append((vaddr, offset, filesz))
        elif kind == PT_DYNAMIC:
            dynamic = (offset, filesz)
        elif kind == PT_INTERP:
            interp = data[offset:offset + filesz].rstrip(b'\0').decode()
    if dynamic is None:
        return interp, []

    def file_offset(address):
        for vaddr, offset, filesz in loads:
            if vaddr <= address < vaddr + filesz:
                return offset + address - vaddr
        raise ElfError(f'address {address:#x} is not mapped from the file')

    entries = []
    offset, size = dynamic
    for position in range(offset, offset + size - 7, 8):
        tag, value = struct.unpack_from('<iI', data, position)
        if tag == 0:
            break
        entries.append((tag, value))
    strtab = next((v for t, v in entries if t == DT_STRTAB), None)
    if strtab is None:
        raise ElfError('dynamic section without a string table')
    start = file_offset(strtab)
    needed = []
    for tag, value in entries:
        if tag == DT_NEEDED:
            end = data.index(b'\0', start + value)
            needed.append(data[start + value:end].decode())
    return interp, needed


def resolve(root, guest, hops=40):
    """Host path for a guest path, following symlinks inside the runtime root."""
    parts = [p for p in guest.split('/') if p]
    current = '/'
    while parts:
        name = parts.pop(0)
        if name == '.':
            continue
        if name == '..':
            current = posixpath.dirname(current.rstrip('/')) or '/'
            continue
        candidate = posixpath.join(current, name)
        host = os.path.join(root, candidate.lstrip('/'))
        if os.path.islink(host):
            hops -= 1
            if hops < 0:
                return None
            target = os.readlink(host)
            if target.startswith('/'):
                current = '/'
            parts = [p for p in target.split('/') if p] + parts
            continue
        if not os.path.lexists(host):
            return None
        current = candidate
    return os.path.join(root, current.lstrip('/'))


def missing_libraries(root, program):
    """Names that cannot be resolved, for program and its libraries (recursive)."""
    root = os.fspath(root)
    missing, seen = [], set()
    queue = [(program, program)]
    while queue:
        guest, parent = queue.pop()
        host = resolve(root, guest)
        if host is None or not os.path.isfile(host):
            missing.append(f'{guest} (needed by {parent})')
            continue
        real = os.path.realpath(host)
        if real in seen:
            continue
        seen.add(real)
        try:
            interp, needed = read_elf32(host)
        except (ElfError, OSError, ValueError, struct.error) as error:
            missing.append(f'{guest}: {error}')
            continue
        if interp:
            queue.append((interp, guest))
        for name in needed:
            found = next((posixpath.join(d, name) for d in SEARCH if resolve(root, posixpath.join(d, name))),
                         None)
            if found is None:
                missing.append(f'{name} (needed by {guest})')
            else:
                queue.append((found, guest))
    return missing
