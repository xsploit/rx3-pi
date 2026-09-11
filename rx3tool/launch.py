"""Start, stop and inspect the RX3 player and its helpers.

Privileged actions are limited to: bind-mounting /dev/{null,zero,urandom,full},
/dev/snd and /proc/asound into the runtime, mounting the configured music USB
read-only inside it, and running the player with `chroot` as your own user.
Every such command is printed before it runs; --dry-run prints only.
"""
from contextlib import nullcontext
import platform
import fcntl
import os
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
from pathlib import Path

from . import REPO
from .assemble import read_marker
from .safefs import Tree, real_directory_chain
from .system import mount_at, mounts, player_pids, processes, runtime_mounts
from .ui import Failure, info, ok, say, show_command, stage, warn

FRAME_BYTES = 4096 + 2 * 1280 * 800 * 4
UI_STATE = struct.pack('<I6fII', 0x52583332, 1, .6, 0, 1, .5, .5, 0, 1)
BIND_DEVICES = ['null', 'zero', 'urandom', 'full']
USB1 = 'media/usb1/sda1'
USB2 = 'media/usb2/sdb1'
LIBRARY_PARTS = ['Contents', 'Music', 'PIONEER/Artwork']
STOP_ORDER = ['midi', 'touch', 'player', 'display']
SUPPORTED_USB = {'vfat': 'tested', 'exfat': 'untested'}


class Launcher:
    def __init__(self, config, dry_run=False):
        self.config = config
        self.dry_run = dry_run
        self.runtime = config.runtime
        self.build = config.build
        self.state = config.state
        self.logs = self.state / 'logs'
        self._sudo_ready = False

    # -- helpers ------------------------------------------------------------
    def rt(self, relative):
        return self.runtime / relative

    def lock(self):
        if self.dry_run:
            return nullcontext()
        self.state.mkdir(parents=True, exist_ok=True)
        handle = open(self.state / 'rx3.lock', 'w')
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Failure('Another ./rx3 start or stop is running', 'Wait for it to finish.')
        return handle

    def require_user(self):
        if os.geteuid() == 0:
            raise Failure('Run ./rx3 as your normal user, not with sudo or as root',
                          'It asks for your password only for the mount and chroot steps.')

    def sudo(self, argv, check=True, capture=False):
        show_command(argv, privileged=True, dry_run=self.dry_run)
        if self.dry_run:
            return subprocess.CompletedProcess(argv, 0, '', '')
        self.ensure_sudo()
        return subprocess.run(['sudo', '-n', '--'] + [str(a) for a in argv], check=check,
                              capture_output=capture, text=True)

    def ensure_sudo(self):
        if self._sudo_ready or self.dry_run:
            return
        if not shutil.which('sudo'):
            raise Failure('sudo is not installed', 'Install it as root: apt install sudo')
        if subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode != 0:
            if not sys.stdin.isatty():
                raise Failure('Administrator rights are needed for mounts and chroot',
                              'Run ./rx3 start from a terminal so sudo can ask for your password.')
            say('  Administrator rights are needed for the mount and chroot steps shown above.')
            if subprocess.run(['sudo', '-v']).returncode != 0:
                raise Failure('sudo did not grant administrator rights')
        self._sudo_ready = True

    def check_target(self, relative):
        """Mount targets must be real directories/files inside the runtime (no symlinks)."""
        if not real_directory_chain(self.runtime, relative):
            raise Failure(f'Runtime path {relative} is missing or passes through a symlink',
                          'Repair the runtime with: ./rx3 assemble')
        return self.rt(relative)

    # -- mounts -------------------------------------------------------------
    def bind(self, source, relative, readonly=False, problems=None):
        target = self.check_target(relative)
        existing = mount_at(target)
        if existing:
            try:
                same = os.path.samefile(source, target)
            except OSError:
                same = False
            if not same:
                raise Failure(f'Something else is mounted at {target}; left unchanged',
                              'Inspect it with: findmnt ' + str(target))
        else:
            self.sudo(['mount', '--bind', source, target])
            existing = None if self.dry_run else mount_at(target)
        if readonly and not self.dry_run and existing and 'ro' not in existing['options']:
            self.sudo(['mount', '-o', 'remount,bind,ro', target])
        elif readonly and self.dry_run:
            self.sudo(['mount', '-o', 'remount,bind,ro', target])

    def prepare_mounts(self):
        stage('Preparing runtime mounts')
        for name in BIND_DEVICES:
            self.bind(f'/dev/{name}', f'dev/{name}')
        if not Path('/dev/snd').is_dir():
            raise Failure('/dev/snd does not exist: no sound devices', 'Connect the controller.')
        self.bind('/dev/snd', 'dev/snd')
        # Keep the emulated /proc files; only ALSA's subtree comes from the host.
        self.bind('/proc/asound', 'proc/asound')
        ok('Device and ALSA bind mounts ready')
        return self.prepare_usb()

    def usb_device(self):
        uuid = self.config.get('usb', 'uuid')
        if not uuid:
            return None, None
        device = Path('/dev/disk/by-uuid') / uuid
        if not device.exists():
            return uuid, None
        return uuid, device

    def usb_fstype(self, device):
        result = subprocess.run(['lsblk', '-no', 'FSTYPE', str(device)], capture_output=True, text=True)
        return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else ''

    def prepare_usb(self):
        uuid, device = self.usb_device()
        if not uuid:
            info('No music USB configured ([usb] uuid is empty); the player starts without media.')
            return False
        target = self.check_target(USB1)
        current = mount_at(target)
        if current:
            actual = subprocess.run(['findmnt', '-n', '-o', 'UUID', '-M', str(target)],
                                    capture_output=True, text=True).stdout.strip()
            if actual.lower() != uuid.lower():
                raise Failure(f'A different filesystem is mounted at {target}; left unchanged')
            if 'ro' not in current['options']:
                raise Failure(f'The music USB is mounted writable at {target}; left unchanged',
                              'Stop RX3 (./rx3 stop) so it can be mounted read-only again.')
            ok(f'Music USB {uuid} already mounted read-only')
        elif device is None:
            warn(f'Music USB {uuid} is not connected; starting without media')
            return False
        else:
            fstype = self.usb_fstype(device)
            if fstype not in SUPPORTED_USB:
                raise Failure(f'The music USB uses {fstype or "an unknown filesystem"}, which is not supported',
                              'Supported: FAT32 (vfat, tested) and exFAT (untested). '
                              'rekordbox USB exports are normally FAT32.')
            if SUPPORTED_USB[fstype] == 'untested':
                warn(f'{fstype} music USBs have not been tested with this runtime')
            host = [m for m in mounts() if m['root'] == '/' and not
                    (m['target'] == str(self.runtime) or m['target'].startswith(str(self.runtime) + '/'))
                    and os.path.realpath(m['source']) == os.path.realpath(device)]
            if host:
                options = host[0]['options']
                if fstype == 'vfat' and not ({'utf8', 'utf8=1', 'iocharset=utf8'} & options):
                    raise Failure(f'The USB is already mounted at {host[0]["target"]} without UTF-8 file names',
                                  'Unmount it in the desktop (eject) and run ./rx3 start again.')
                self.bind(host[0]['target'], USB1, readonly=True)
            else:
                uid, gid = self.config.uid(), self.config.gid()
                charset = 'utf8=1' if fstype == 'vfat' else 'iocharset=utf8'
                self.sudo(['mount', '-t', fstype, '-o',
                           f'ro,uid={uid},gid={gid},{charset},nosuid,nodev,noexec', device, target])
            ok(f'Music USB {uuid} mounted read-only at {USB1} inside the runtime')
        if not self.dry_run:
            self.prepare_library()
        return True

    def prepare_library(self):
        """Writable local copy of the rekordbox database/analysis; music stays read-only."""
        src = self.rt(USB1)
        dst_rel = USB2
        dst = self.check_target(dst_rel)
        if mount_at(dst):
            raise Failure(f'{dst} is itself a mount point; inspect before replacing it')
        copied = 0
        with Tree(self.runtime) as tree:
            stamp = f'{dst_rel}/.rx3-usb-uuid'
            uuid = self.config.get('usb', 'uuid').lower()
            if tree.lstat(stamp) is not None:
                with tree.open_read(stamp) as handle:
                    previous = handle.read().decode().strip()
                if previous != uuid:
                    raise Failure('This runtime holds a library copy from a different USB',
                                  'Keep this runtime to preserve edits. Configure a new runtime directory, '
                                  'then run ./rx3 assemble, build and install for the new USB.')
            elif any(dst.iterdir()):
                raise Failure('Existing local USB library has no UUID record; left unchanged',
                              'Use a new runtime directory so existing library edits are preserved.')
            else:
                tree.write(stamp, (uuid + '\n').encode(), 0o600)
            db = src / 'PIONEER' / 'rekordbox'
            if db.is_dir():
                for item in sorted(db.iterdir()):
                    rel = f'{dst_rel}/PIONEER/rekordbox/{item.name}'
                    if item.is_file() and not item.is_symlink() and tree.lstat(rel) is None:
                        with item.open('rb') as handle:
                            tree.write(rel, handle, 0o644)
                        copied += 1
            pioneer = src / 'PIONEER'
            if pioneer.is_dir():
                for item in sorted(pioneer.iterdir()):
                    rel = f'{dst_rel}/PIONEER/{item.name}'
                    if item.is_file() and not item.is_symlink() and tree.lstat(rel) is None:
                        with item.open('rb') as handle:
                            tree.write(rel, handle, 0o644)
                        copied += 1
            for part in LIBRARY_PARTS:
                if (src / part).is_dir():
                    tree.mkdir(f'{dst_rel}/{part}', 0o755)
            analysis = src / 'PIONEER' / 'USBANLZ'
            tree.mkdir(f'{dst_rel}/PIONEER/USBANLZ', 0o755)
            if analysis.is_dir():
                for folder, dirs, files in os.walk(analysis):
                    dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(folder, d)))
                    rel_folder = os.path.relpath(folder, analysis)
                    base = f'{dst_rel}/PIONEER/USBANLZ' + ('' if rel_folder == '.' else f'/{rel_folder}')
                    tree.mkdir(base, 0o755)
                    for name in sorted(files):
                        path = os.path.join(folder, name)
                        # Never overwrite: the player saves cue/grid edits into these copies.
                        if not os.path.islink(path) and tree.lstat(f'{base}/{name}') is None:
                            with open(path, 'rb') as handle:
                                tree.write(f'{base}/{name}', handle, 0o644)
                            copied += 1
                            if copied % 500 == 0:
                                info(f'{copied} library files copied ...')
        for part in LIBRARY_PARTS:
            if (src / part).is_dir():
                self.bind(src / part, f'{dst_rel}/{part}', readonly=True)
        if not (dst / 'PIONEER' / 'rekordbox').is_dir():
            warn('The USB has no PIONEER/rekordbox folder; export your library with rekordbox first')
        ok(f'Local library view ready ({copied} new files copied; existing edits kept)')

    def unmount_all(self):
        targets = runtime_mounts(self.runtime)
        if not targets:
            return
        stage('Releasing runtime mounts')
        for target in targets:
            result = self.sudo(['umount', target], check=False, capture=True)
            if result.returncode:
                warn(f'Could not unmount {target}: {(result.stderr or "").strip()}',
                     'Something may still use it. Check with: fuser -vm ' + target)
        if not self.dry_run and runtime_mounts(self.runtime):
            warn('Some runtime mounts remain; see messages above')
        else:
            ok('All runtime mounts released')

    # -- processes ------------------------------------------------------------
    def helpers(self):
        """Running helper processes that belong to this runtime, by kind."""
        runtime = str(self.runtime)
        fb = runtime + '/dev/fb0'
        touch = runtime + '/dev/tsc2007_2-0048'
        control = runtime + '/dev/rx3-control'
        found = {kind: [] for kind in STOP_ORDER}
        found['player'] = player_pids(self.runtime)
        me = os.getuid()
        for pid, uid, argv, comm in processes():
            if uid != me or not argv:
                continue
            exe = os.path.basename(argv[0])
            if exe == 'rx3-fb-present' and len(argv) > 1 and argv[1] == fb:
                found['display'].append(pid)
            elif exe == 'rx3-touch-bridge' and len(argv) > 2 and argv[2] == touch:
                found['touch'].append(pid)
            elif exe.startswith('python') and len(argv) > 1 and os.path.basename(argv[1]) == 'flx6-rx3.py':
                if '--fifo' in argv and (argv.index('--fifo') + 1 < len(argv)
                                            and argv[argv.index('--fifo') + 1] == control):
                    found['midi'].append(pid)
        return found

    def spawn(self, name, argv, env=None):
        log = self.logs / f'{name}.log'
        show_command(argv, dry_run=self.dry_run)
        if self.dry_run:
            return None
        self.logs.mkdir(parents=True, exist_ok=True)
        if log.exists():
            log.replace(self.logs / f'{name}.previous.log')
        with log.open('wb') as handle:
            process = subprocess.Popen([str(a) for a in argv], stdin=subprocess.DEVNULL, stdout=handle,
                                       stderr=subprocess.STDOUT, start_new_session=True,
                                       env=dict(os.environ, **(env or {})), cwd=str(self.state))
        return process

    def player_command(self):
        uid, gid = self.config.uid(), self.config.gid()
        groups = ','.join(str(g) for g in self.config.groups())
        command = ['chroot', f'--userspec={uid}:{gid}']
        if groups:
            command.append(f'--groups={groups}')
        return command + [str(self.runtime), '/bin/busybox', 'env', 'LD_PRELOAD=/lib/fbshim.so',
                          '/root/pdj/rbp-pi', '-a']

    def preflight(self):
        self.require_user()
        self.config.require_valid()
        if platform.machine() not in ('aarch64', 'arm64', 'armv7l', 'armv8l'):
            raise Failure('Starting RX3 requires an ARM Raspberry Pi; this host can run offline checks only.')
        if not player_pids(self.runtime) and any(comm == 'rbp-pi' for _, _, _, comm in processes()):
            raise Failure('Another RX3 player is running and cannot be identified as this runtime',
                          'Stop it using its original launcher before starting this installation.')
        from .doctor import Doctor
        if Doctor(self.config, ('runtime', 'devices')).run():
            raise Failure('Startup checks failed; fix the doctor failures above before starting.')
        marker = read_marker(self.runtime)
        if marker is None:
            raise Failure(f'No assembled runtime at {self.runtime}',
                          'Follow the setup steps: ./rx3 setup  (or ./rx3 assemble, build, install)')
        if 'installed' not in marker:
            raise Failure('The patched player and shim are not installed in the runtime',
                          'Run: ./rx3 build && ./rx3 install')
        for name in ('rx3-fb-present', 'rx3-touch-bridge'):
            if not (self.build / name).is_file():
                raise Failure(f'{self.build / name} is missing', 'Run: ./rx3 build')
        drm, how = self.config.drm_device()
        touch, touch_how = self.config.touch_device()
        mapping = self.config.path('controller', 'mapping')
        if not mapping.is_file():
            raise Failure(f'Controller mapping not found: {mapping}',
                          'Set [controller] mapping in rx3.conf to your Pioneer-DDJ-FLX6.midi.xml')
        return drm, how, touch, touch_how, mapping

    def start(self):
        say(f'Starting RX3 from {self.runtime}')
        drm, drm_how, touch, touch_how, mapping = self.preflight()
        with self.lock():
            running = self.helpers()
            new_player = not running['player']
            usb = False
            if new_player:
                usb = self.prepare_mounts()
                if not self.dry_run:
                    with Tree(self.runtime) as tree:
                        tree.sparse_file('dev/rx3-present-frame', FRAME_BYTES, 0o600)
                        tree.write('dev/rx3-ui-state', UI_STATE, 0o600)
                stage('Starting the player')
                if not self.dry_run:
                    self.ensure_sudo()
                player_process = self.spawn('player', ['sudo', '-n', '--'] + self.player_command())
            else:
                ok(f"Player already running (process {running['player'][0]})")
            env = {'RX3_RUNTIME': str(self.runtime), 'RX3_DRM_DEVICE': drm,
                   'RX3_FB_DEVICE': self.config.get('display', 'fb_device')}
            if not running['display']:
                info(f'Display: {drm} ({drm_how})')
                self.spawn('display', [self.build / 'rx3-fb-present', self.rt('dev/fb0'),
                                       '--fullscreen', '--coherent'], env)
            if not running['touch']:
                info(f'Touch: {touch} ({touch_how})')
                self.spawn('touch', [self.build / 'rx3-touch-bridge', touch,
                                     self.rt('dev/tsc2007_2-0048'), '--fullscreen'], env)
            if not running['midi']:
                self.spawn('midi', [sys.executable, REPO / 'flx6-rx3.py', '--mapping', mapping,
                                    '--fifo', self.rt('dev/rx3-control'),
                                    '--state', self.state / 'midi-jog-state.json',
                                    '--port-name', self.config.get('controller', 'midi_name'),
                                    '--player-id', ('dry-run' if self.dry_run else str(player_process.pid)
                                                    if new_player else str(running['player'][0]))], env)
            if self.dry_run:
                return
            if not new_player:
                say('RX3 already running; restored any missing display, touch and MIDI helpers.')
                return
            stage('Waiting for the player to initialise')
            # Storage workers start after the display; USB events before then are lost.
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if player_process.poll() is not None:
                    break
                time.sleep(.5)
            if player_process.poll() is not None:
                tail = log_tail(self.logs / 'player.log')
                raise Failure('The player exited during startup', 'Last lines of the player log:\n' + tail)
            if usb:
                self.notify('proc/udev_usb1', b'mount /media/usb1/sda1')
                if mount_at(self.rt(USB2 + '/Contents')):
                    self.notify('proc/udev_usb2', b'mount /media/usb2/sdb1')
            missing = [kind for kind, pids in self.helpers().items() if kind != 'player' and not pids]
            if missing:
                raise Failure('Helpers exited: ' + ', '.join(missing),
                              f'Inspect logs in {self.logs}; run ./rx3 stop before retrying.')
            stage('RX3 is running')
            info(f'Logs: {self.logs}')
            info('Stop it with: ./rx3 stop')

    def notify(self, relative, message):
        path = self.check_target(relative)
        st = os.lstat(path)
        if not stat.S_ISFIFO(st.st_mode):
            raise Failure(f'{relative} in the runtime is not a FIFO; repair with ./rx3 assemble')
        fd = os.open(path, os.O_RDWR | os.O_NONBLOCK | os.O_NOFOLLOW)
        try:
            os.write(fd, message)
        finally:
            os.close(fd)
        ok(f'Sent "{message.decode()}" to the player')

    def stop(self, keep_mounts=False):
        self.require_user()
        self.config.require_valid()
        if read_marker(self.runtime) is None:
            raise Failure('Refusing to stop/unmount an unrecognized runtime directory')
        with self.lock():
            found = self.helpers()
            if not any(found.values()):
                say('RX3 is not running.')
            for kind in STOP_ORDER:
                for pid in found[kind]:
                    say(f'  Stopping {kind} (process {pid})')
                    if self.dry_run:
                        continue
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    except PermissionError:
                        self.sudo(['kill', '-TERM', str(pid)], check=False)
                if self.dry_run:
                    continue
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and self.helpers()[kind]:
                    time.sleep(.05)
                if self.helpers()[kind]:
                    raise Failure(f'{kind} did not stop cleanly; left it running for inspection',
                                  f'Logs: {self.logs}')
            if not keep_mounts:
                self.unmount_all()
            say('RX3 stopped; MIDI, audio and display released.')

    def status(self):
        found = self.helpers()
        say(f'Runtime: {self.runtime}')
        for kind in ('player', 'display', 'touch', 'midi'):
            pids = found[kind]
            say(f'  {kind:8} ' + (f'running (process {", ".join(map(str, pids))})' if pids else 'stopped'))
        targets = runtime_mounts(self.runtime)
        say(f'  mounts   {len(targets)} inside the runtime')
        for target in sorted(targets):
            info(target)
        say(f'  logs     {self.logs}')
        return any(found.values())


def log_tail(path, lines=15):
    try:
        return '\n'.join(path.read_text(errors='replace').splitlines()[-lines:])
    except OSError:
        return '(no log)'
