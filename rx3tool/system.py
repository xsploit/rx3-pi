"""Read-only views of mounts and processes, shared by setup, doctor and launch."""
import os
import re

MOUNTINFO = '/proc/self/mountinfo'


def unescape(field):
    """Undo the octal escapes (\\040 for space, ...) used in /proc mount tables."""
    return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), field)


def mounts(mountinfo=MOUNTINFO):
    """List of dicts: target, root (subtree), fstype, source, options."""
    result = []
    try:
        with open(mountinfo, encoding='utf-8', errors='surrogateescape') as handle:
            lines = handle.read().splitlines()
    except OSError:
        return result
    for line in lines:
        left, sep, right = line.partition(' - ')
        fields = left.split(' ')
        extra = right.split(' ')
        if not sep or len(fields) < 6 or len(extra) < 3:
            continue
        result.append({'root': unescape(fields[3]), 'target': unescape(fields[4]),
                       'options': set(fields[5].split(',')) | set(extra[2].split(',')),
                       'fstype': extra[0], 'source': unescape(extra[1])})
    return result


def runtime_mounts(runtime, mountinfo=MOUNTINFO):
    """Mount points inside the runtime, deepest first."""
    root = os.path.realpath(runtime)
    found = {m['target'] for m in mounts(mountinfo)
             if m['target'] == root or m['target'].startswith(root + '/')}
    return sorted(found, key=lambda p: (p.count('/'), len(p)), reverse=True)


def mount_at(target, mountinfo=MOUNTINFO):
    """The last (visible) mount whose target is exactly `target`, or None."""
    target = os.path.realpath(target)
    found = [m for m in mounts(mountinfo) if m['target'] == target]
    return found[-1] if found else None


def mount_containing(path, mountinfo=MOUNTINFO):
    path = os.path.realpath(path)
    best = None
    for m in mounts(mountinfo):
        target = m['target']
        if path == target or path.startswith(target.rstrip('/') + '/'):
            if best is None or len(target) >= len(best['target']):
                best = m
    return best


def processes():
    """Yield (pid, uid, argv list, comm) for every visible process."""
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/cmdline', 'rb') as handle:
                argv = [os.fsdecode(a) for a in handle.read().split(b'\0') if a]
            with open(f'/proc/{entry}/comm') as handle:
                comm = handle.read().strip()
            uid = os.stat(f'/proc/{entry}').st_uid
        except OSError:
            continue
        yield int(entry), uid, argv, comm


def process_root(pid):
    try:
        return os.readlink(f'/proc/{pid}/root')
    except OSError:
        return None


def player_pids(runtime):
    """rbp-pi processes whose root directory is confirmed to be this runtime."""
    root = os.path.realpath(runtime)
    result = []
    for pid, _, argv, comm in processes():
        # sudo stays as the launcher/monitor and forwards TERM to its child.
        if argv[:4] == ['sudo', '-n', '--', 'chroot'] and root in argv[4:]:
            result.append(pid)
            continue
        if comm != 'rbp-pi':
            continue
        seen = process_root(pid)
        if seen == root:
            result.append(pid)
    return result


def running(names):
    """PIDs of processes whose comm is in names."""
    return [(pid, comm) for pid, _, _, comm in processes() if comm in names]
