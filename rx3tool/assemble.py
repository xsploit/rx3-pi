"""Assemble the RX3 runtime directory (the chroot) from recovered images.

The runtime is built only from the hash-verified firmware images plus a small
set of emulated device and /proc files that replace RX3 hardware. Re-running
is safe: unchanged firmware files are skipped, emulated files are checked,
and nothing the player wrote (settings, the local library copy) is removed.
Nothing here needs root; the bind mounts happen later, at start.
"""
import json
import stat
import tarfile
import time

from . import REPO
from .cramfs import extract as extract_cramfs, Image
from .recover import RELEASE, sha256_file
from .safefs import Tree
from .system import mount_containing, player_pids, runtime_mounts
from .ui import Failure, info, ok, say, stage, warn

MARKER = '.rx3-runtime.json'
FORMAT = 1
FB_BYTES = 1280 * 800 * 4
VIVANTE = 'usr/lib/directfb-1.4-0/gfxdrivers/libdirectfb_gal.so'
VIVANTE_DISABLED = 'usr/lib/directfb-1.4-0/gfxdrivers-disabled/libdirectfb_gal.so'

# Emulated RX3 hardware. Guest paths are what the firmware opens inside the chroot.
FIFOS = [
    'dev/rx3-control',         # control-shim.c: native key queue commands
    'dev/tsc2007_2-0048',      # touch-bridge.c -> firmware touch reports
    'dev/subucom_spi1.0',      # panel CPU links; ioctls are answered by fbshim.c
    'dev/subucom_spi2.0',
    'dev/subucom_spi_rdy3.0',
    'dev/subucom_spi_rdy4.0',
    'proc/udev_usb1',          # "mount /media/usb1/sda1" notifications
    'proc/udev_usb2',
]
# Empty placeholders that become bind mounts of the host devices at start.
BIND_FILES = ['dev/null', 'dev/zero', 'dev/urandom', 'dev/full']
BIND_DIRS = ['dev/snd', 'proc/asound']
DIRECTORIES = ['root/settings', 'media/usb1/sda1', 'media/usb2/sdb1', 'var/run', 'var/lock',
               'var/log']
STICKY = ['tmp', 'var/tmp']
CPUINFO = (
    '# Emulated for the RX3 compatibility runtime; not the real CPU.\n'
    'processor\t: 0\n'
    'model name\t: ARMv7 Processor rev 10 (v7l)\n'
    'Features\t: half thumb fastmult vfp edsp neon vfpv3 tls\n'
    'CPU architecture: 7\n'
    '\n'
    'Hardware\t: RX3 compatibility runtime\n'
    'Revision\t: 0000\n'
)
# The player looks up USB filesystem types here (FAT is its default).
MOUNTS = (
    'rootfs / rootfs rw 0 0\n'
    '/dev/sda1 /media/usb1/sda1 vfat ro 0 0\n'
    '/dev/sdb1 /media/usb2/sdb1 vfat rw 0 0\n'
)


def asound_conf(card):
    """The tested asound.conf with the configured ALSA card ID."""
    text = (REPO / 'asound.conf').read_text()
    if 'CARD=DDJFLX6' not in text:
        raise Failure('asound.conf template no longer names CARD=DDJFLX6')
    return text.replace('CARD=DDJFLX6', f'CARD={card}')


def read_marker(runtime):
    try:
        with Tree(runtime) as tree, tree.open_read(MARKER) as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) and data.get('format') == FORMAT else None
    except (OSError, ValueError, Failure):
        return None


def write_marker(runtime, marker):
    with Tree(runtime) as tree:
        tree.write(MARKER, (json.dumps(marker, indent=2) + "\n").encode(), 0o600)


class Assembler:
    def __init__(self, config, dry_run=False, repair=False):
        self.config = config
        self.dry_run = dry_run
        self.repair = repair
        self.runtime = config.runtime
        self.images = config.firmware_dir / 'images'

    def check_inputs(self):
        missing = []
        for name, digest in RELEASE['images'].items():
            path = self.images / name
            if not path.is_file():
                missing.append(str(path))
            elif sha256_file(path) != digest:
                raise Failure(f'{path} differs from the recovered RX3 1.19 image',
                              'Run ./rx3 recover again to restore it.')
        if missing:
            raise Failure('Recovered firmware images are missing:\n  ' + '\n  '.join(missing),
                          'Run ./rx3 recover first.')
        ok(f'Recovered RX3 {RELEASE["version"]} images verified in {self.images}')

    def check_target(self):
        runtime = self.runtime
        if runtime.is_symlink():
            raise Failure(f'The runtime path is a symlink: {runtime}',
                          'Point [paths] runtime at the real directory instead.')
        if runtime.exists():
            if not runtime.is_dir():
                raise Failure(f'The runtime path exists and is not a directory: {runtime}')
            marker = read_marker(runtime)
            if marker is None and any(runtime.iterdir()):
                raise Failure(f'{runtime} is not empty and was not created by this tool',
                              'Choose an empty or new directory for [paths] runtime. An existing\n'
                              'hand-made runtime can be kept; see README "Existing installations".')
            if marker and marker.get('format', 0) > FORMAT:
                raise Failure(f'{runtime} was created by a newer version of this tool')
        mounts = runtime_mounts(runtime)
        if mounts:
            raise Failure('The runtime still has active mounts: ' + ', '.join(mounts),
                          'Stop the player and release them with: ./rx3 stop')
        if player_pids(runtime):
            raise Failure('The RX3 player is running from this runtime', 'Stop it first: ./rx3 stop')
        filesystem_check(runtime)

    def run(self):
        say(f'Assembling the RX3 runtime in {self.runtime}')
        self.check_inputs()
        self.check_target()
        if self.dry_run:
            with Image(self.images / 'rootfs.cramfs') as image:
                counts = {}
                for kind, *_ in image.walk():
                    counts[kind] = counts.get(kind, 0) + 1
            say(f'  [dry-run] would write {counts.get("file", 0)} files, {counts.get("dir", 0)} '
                f'directories and {counts.get("symlink", 0)} symlinks from rootfs.cramfs')
            say('  [dry-run] would add the player (root/pdj), GUI data (root/gui), '
                f'{len(FIFOS)} FIFOs, emulated /dev and /proc files and etc/asound.conf '
                f'for ALSA card {self.config.get("audio", "card")}')
            return
        self.runtime.mkdir(parents=True, exist_ok=True)
        marker = read_marker(self.runtime) or {"format": FORMAT, "firmware": RELEASE["version"]}
        marker["state"] = "assembling"
        write_marker(self.runtime, marker)
        with Tree(self.runtime) as tree:
            stage('Writing the firmware root filesystem')
            stats, links = extract_cramfs(self.images / 'rootfs.cramfs', tree, replace=self.repair)
            ok(f"{stats['files']} files written, {stats['unchanged']} already present, "
               f"{stats['symlinks']} symlinks, {stats['special']} device nodes skipped")
            stage('Adding the RX3 player and GUI data')
            for image, prefix in (('pdj.tar.gz', 'root'), ('gui.tar.gz', 'root/gui'),
                                  ('settings.tar.gz', 'root/settings')):
                count = extract_tar(self.images / image, tree, prefix, replace=self.repair)
                ok(f'{image}: {count} files written')
            player = self.runtime / 'root/pdj/rbp'
            if sha256_file(player) != RELEASE['player_sha256']:
                raise Failure(f'{player} is not the verified RX3 1.19 player')
            ok('Original RX3 1.19 player verified: root/pdj/rbp')
            stage('Preparing emulated RX3 hardware')
            self.emulate(tree)
            stage('Audio routing')
            text = asound_conf(self.config.get('audio', 'card')).encode()
            original = tree.lstat('etc/asound.conf.firmware')
            current = tree.lstat('etc/asound.conf')
            if original is None and current is not None:
                with tree.open_read('etc/asound.conf') as handle:
                    tree.write('etc/asound.conf.firmware', handle.read(), 0o644)
            tree.write('etc/asound.conf', text, 0o644)
            ok(f'etc/asound.conf routes master to channels 1/2 and headphones to 3/4 of '
               f'ALSA card {self.config.get("audio", "card")}')
        marker = read_marker(self.runtime) or {}
        marker.update({'format': FORMAT, 'firmware': RELEASE['version'],
                       'player_sha256': RELEASE['player_sha256'], 'assembled': time.time(),
                       'symlinks': len(links), 'state': 'assembled'})
        write_marker(self.runtime, marker)
        stage('Runtime assembled')
        info(str(self.runtime))
        say('\nNext step: ./rx3 build   (then ./rx3 install)')

    def emulate(self, tree):
        for path in DIRECTORIES:
            tree.mkdir(path, 0o755)
        for path in STICKY:
            tree.mkdir(path, 0o1777)
            tree.chmod_dir(path, 0o1777)
        for path in BIND_DIRS:
            tree.mkdir(path, 0o755)
        for path in BIND_FILES:
            st = tree.lstat(path)
            if st is None:
                tree.write(path, b'', 0o666)
            elif not stat.S_ISREG(st.st_mode) and not stat.S_ISCHR(st.st_mode):
                raise Failure(f'Unexpected file type at {path} in the runtime')
        created = sum(tree.fifo(path, 0o660) for path in FIFOS)
        ok(f'{len(FIFOS)} FIFOs present ({created} created): control, touch, panel links, USB events')
        tree.sparse_file('dev/fb0', FB_BYTES, 0o660)
        ok('dev/fb0 is a 1280x800 32-bit regular file (never the host framebuffer)')
        # GpioManager reads one byte per GPIO at its number; all inputs idle high.
        gpio = tree.lstat('dev/gpiodrv')
        if gpio is None or gpio.st_size != 4096:
            tree.write('dev/gpiodrv', b'\x01' * 4096, 0o660)
        ok('dev/gpiodrv emulates idle GPIO inputs')
        tree.write('proc/cpuinfo', CPUINFO.encode(), 0o444)
        tree.write('proc/mounts', MOUNTS.encode(), 0o444)
        ok('proc/cpuinfo and proc/mounts are small emulated files (host /proc is not mounted)')
        st = tree.lstat(VIVANTE)
        if st is not None and stat.S_ISREG(st.st_mode):
            if tree.lstat(VIVANTE_DISABLED) is None:
                tree.rename(VIVANTE, VIVANTE_DISABLED)
            else:
                tree.unlink(VIVANTE)  # re-extracted by a later run
        if tree.lstat(VIVANTE_DISABLED) is None:
            raise Failure('Expected the firmware Vivante DirectFB driver in the runtime')
        ok('Vivante GPU driver disabled; DirectFB renders in software')


def extract_tar(path, tree, prefix, replace=False):
    """Extract directories, regular files and symlinks of a firmware tarball."""
    count = 0
    with tarfile.open(path, mode='r|gz') as archive:
        for member in archive:
            name = member.name
            while name.startswith('./'):
                name = name[2:]
            name = name.strip('/')
            if not name or name == '.':
                continue
            relative = f'{prefix}/{name}'
            if member.isdir():
                tree.mkdir(relative, (member.mode & 0o777) | 0o700)
            elif member.isfile():
                existing = tree.lstat(relative)
                if existing is not None and not replace and stat.S_ISREG(existing.st_mode) \
                        and existing.st_size == member.size:
                    continue
                with archive.extractfile(member) as source:
                    tree.write(relative, source, (member.mode & 0o777) | 0o600)
                count += 1
            elif member.issym():
                tree.symlink(relative, member.linkname, replace=replace)
            else:
                warn(f'Skipped special file {name} in {path.name}')
    return count


UNSUITABLE_FS = {'vfat', 'msdos', 'exfat', 'ntfs', 'ntfs3', 'fuseblk', 'nfs', 'nfs4', 'cifs', 'smb3',
                 'iso9660'}


def filesystem_check(runtime):
    """The runtime needs symlinks, FIFOs, Unix permissions and exec (not FAT/NTFS/noexec)."""
    probe = runtime
    while not probe.exists():
        probe = probe.parent
    found = mount_containing(probe)
    if found is None:
        return
    if found['fstype'] in UNSUITABLE_FS:
        raise Failure(f"{runtime} is on a {found['fstype']} filesystem, which cannot hold the runtime",
                      "Use the Pi's own disk (ext4), for example the default work/runtime.")
    if 'noexec' in found['options']:
        raise Failure(f'{runtime} is on a filesystem mounted noexec',
                      "Use a directory on the Pi's own disk.")
