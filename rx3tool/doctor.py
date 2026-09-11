"""./rx3 doctor: read-only checks with concrete fixes, grouped by setup stage.

Nothing here changes the system: it reads /proc, /sys and the configuration,
runs compilers on temporary files, and executes a 32-bit ARM probe program.
"""
import ctypes.util
import os
import platform
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from . import REPO
from .assemble import BIND_DIRS, BIND_FILES, FIFOS, filesystem_check, read_marker
from .config import PANEL, SUPPORTED_FIRMWARE, alsa_cards, detect_drm_cards, detect_touchscreens
from .recover import RELEASE, memory_available
from .system import running
from .ui import Failure, fail, info, ok, say, stage, warn

STAGES = ('recover', 'build', 'runtime', 'devices')
DESKTOPS = {'Xorg', 'Xwayland', 'labwc', 'wayfire', 'weston', 'sway', 'gnome-shell', 'kwin_wayland',
            'cage', 'mutter', 'Hyprland'}
AUDIO_SERVERS = {'pipewire', 'pulseaudio', 'wireplumber', 'jackd'}
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def arm32_probe_elf():
    """A 32-bit ARM Linux program that only calls exit(0) (84 + 12 bytes)."""
    code = struct.pack('<3I', 0xe3a00000, 0xe3a07001, 0xef000000)  # mov r0,#0; mov r7,#1; svc 0
    base, offset = 0x10000, 52 + 32
    header = (b'\x7fELF\x01\x01\x01' + bytes(9) +
              struct.pack('<HHIIIIIHHHHHH', 2, 40, 1, base + offset, 52, 0, 0x05000000, 52, 32, 1,
                          0, 0, 0))
    program = struct.pack('<8I', 1, 0, base, base, offset + len(code), offset + len(code), 5, 0x10000)
    return header + program + code


def arm32_runs():
    """True/False whether this kernel executes 32-bit ARM programs, None if unknown."""
    with tempfile.TemporaryDirectory(prefix='rx3-doctor-') as directory:
        path = Path(directory) / 'arm32-probe'
        path.write_bytes(arm32_probe_elf())
        path.chmod(0o700)
        try:
            return subprocess.run([str(path)], capture_output=True, timeout=10).returncode == 0
        except OSError:
            return False
        except subprocess.TimeoutExpired:
            return None


class Doctor:
    def __init__(self, config, stages=STAGES):
        self.config = config
        self.stages = stages
        self.failures = 0
        self.warnings = 0
        self.packages = []
        self.machine = platform.machine()
        self.is_pi_arm = self.machine in ('aarch64', 'arm64', 'armv7l', 'armv8l')

    def ok(self, message):
        ok(message)

    def warn(self, message, hint=None):
        self.warnings += 1
        warn(message, hint)

    def fail(self, message, hint=None, package=None):
        self.failures += 1
        fail(message, hint)
        if package and package not in self.packages:
            self.packages.append(package)

    def tool(self, name, package, why):
        if shutil.which(name):
            self.ok(f'{name} found ({why})')
            return True
        self.fail(f'{name} is missing ({why})', f'Install: sudo apt install {package}', package)
        return False

    # -- sections -----------------------------------------------------------
    def host(self):
        stage('This computer')
        pretty = ''
        try:
            for line in Path('/etc/os-release').read_text().splitlines():
                if line.startswith('PRETTY_NAME='):
                    pretty = line.split('=', 1)[1].strip('"')
        except OSError:
            pass
        model = ''
        try:
            model = Path('/proc/device-tree/model').read_bytes().rstrip(b'\0').decode(errors='replace')
        except OSError:
            pass
        info(f'{pretty or platform.system()} on {self.machine}' + (f', {model}' if model else ''))
        if sys.version_info < (3, 9):
            self.fail(f'Python {platform.python_version()} is too old; 3.9 or newer is needed',
                      'Use Raspberry Pi OS / Debian 12 (Bookworm) or newer.')
        else:
            self.ok(f'Python {platform.python_version()}')
        if not self.is_pi_arm:
            warn(f'This is a {self.machine} computer, not the Raspberry Pi.',
                 'Here you can run ./rx3 recover and the offline tests (./rx3 selftest).\n'
                 'The player starts only on a Raspberry Pi 5; recovery, assembly and cross-builds\n'
                 '(64-bit Raspberry Pi OS / Debian). Windows and x86 desktops cannot run it.')
        elif 'Raspberry Pi 5' not in model:
            self.warn(f'Tested only on a Raspberry Pi 5; this is: {model or "unknown hardware"}')
        else:
            self.ok('Raspberry Pi 5 (the tested model)')

    def recover_checks(self):
        stage('Stage 1 - firmware recovery prerequisites')
        try:
            import cryptography  # noqa: F401
            self.ok('Python cryptography module')
        except ImportError:
            self.fail('Python module "cryptography" is missing', 'Install: sudo apt install python3-cryptography',
                      'python3-cryptography')
        if not shutil.which('7z'):
            self.tool('unzip', 'unzip', 'the official source ZIPs use Deflate64')
            self.tool('bsdtar', 'libarchive-tools', 'reads the firmware ISO image')
        else:
            self.ok('7z found (reads the source ZIPs and the ISO image)')
        work = self.config.work
        probe = work
        while not probe.exists():
            probe = probe.parent
        free = shutil.disk_usage(probe).free
        need = 1_000_000_000
        images = self.config.firmware_dir / 'images'
        if all((images / n).is_file() for n in RELEASE['images']):
            self.ok(f'Recovered RX3 {SUPPORTED_FIRMWARE} images present in {images}')
        elif free < need:
            self.fail(f'Only {free / 1e6:.0f} MB free at {probe}; recovery needs about 1000 MB',
                      'Free space or set [paths] work to a bigger local disk.')
        else:
            self.ok(f'{free / 1e6:.0f} MB free at {probe} (recovery needs about 1000 MB)')
        available = memory_available()
        if available is not None:
            if available < 150 * 1048576:
                self.warn(f'Only {available / 1048576:.0f} MiB memory available',
                          'Close the desktop/browser before recovering (peak use is about 100 MiB).')
            else:
                self.ok(f'{available / 1048576:.0f} MiB memory available (recovery peak is about 100 MiB)')

    def build_checks(self):
        stage('Stage 2 - build prerequisites (compatibility helpers)')
        self.tool('gcc', 'build-essential', 'builds the display and touch helpers')
        if self.tool('pkg-config', 'pkg-config', 'finds library compiler flags'):
            for module, package, why in (('libdrm', 'libdrm-dev', 'xf86drm.h for the display'),
                                         ('freetype2', 'libfreetype-dev', 'fonts in the display helper')):
                if subprocess.run(['pkg-config', '--exists', module]).returncode == 0:
                    self.ok(f'{module} development files ({why})')
                else:
                    self.fail(f'{module} development files are missing ({why})',
                              f'Install: sudo apt install {package}', package)
            self.compile_check()
        self.tool('arm-linux-gnueabi-gcc', 'gcc-arm-linux-gnueabi',
                  '32-bit ARM compiler for the player shim')
        self.tool('arm-linux-gnueabi-as', 'binutils-arm-linux-gnueabi', 'assembles the ARM clock stub')
        self.tool('arm-linux-gnueabi-objcopy', 'binutils-arm-linux-gnueabi', 'extracts the clock stub')
        if shutil.which('arm-linux-gnueabi-gcc'):
            self.arm_compile_check()

    def compile_check(self):
        """Catch the 'xf86drm.h: No such file or directory' failure before building."""
        if not shutil.which('gcc'):
            return
        flags = subprocess.run(['pkg-config', '--cflags', '--libs', 'libdrm', 'freetype2'],
                               capture_output=True, text=True)
        if flags.returncode:
            return
        with tempfile.TemporaryDirectory(prefix='rx3-doctor-') as directory:
            source = Path(directory) / 'probe.c'
            source.write_text('#include <xf86drm.h>\n#include <xf86drmMode.h>\n#include <ft2build.h>\n'
                              '#include FT_FREETYPE_H\nint main(void){return drmAvailable()&&0;}\n')
            result = subprocess.run(['gcc', '-o', str(Path(directory) / 'probe'), str(source)]
                                    + flags.stdout.split(), capture_output=True, text=True)
        if result.returncode == 0:
            self.ok('Test program with xf86drm.h and FreeType compiles and links')
        else:
            first = (result.stderr.strip().splitlines() or ['unknown error'])[0]
            self.fail(f'A test program using xf86drm.h does not compile: {first}',
                      'Install: sudo apt install libdrm-dev libfreetype-dev pkg-config\n'
                      'Build with sh build.sh native (it passes the pkg-config flags for you).',
                      'libdrm-dev')

    def arm_compile_check(self):
        with tempfile.TemporaryDirectory(prefix='rx3-doctor-') as directory:
            source = Path(directory) / 'probe.c'
            source.write_text('#include <asm/ioctl.h>\nint probe(int x){return x+_IOC_NRBITS;}\n')
            result = subprocess.run(['arm-linux-gnueabi-gcc', '-march=armv7-a', '-fPIC', '-nostdlib',
                                     '-idirafter', '/usr/include', '-c', '-o',
                                     str(Path(directory) / 'probe.o'), str(source)],
                                    capture_output=True, text=True)
        if result.returncode == 0:
            self.ok('32-bit ARM compiler produces objects')
        else:
            first = (result.stderr.strip().splitlines() or ['unknown error'])[0]
            self.fail(f'The 32-bit ARM compiler does not work: {first}',
                      'Reinstall: sudo apt install gcc-arm-linux-gnueabi linux-libc-dev',
                      'gcc-arm-linux-gnueabi')

    def runtime_checks(self):
        stage('Stage 3 - runtime (assembled RX3 environment)')
        runtime = self.config.runtime
        info(f'Runtime: {runtime}')
        try:
            filesystem_check(runtime)
            self.ok('Runtime location supports symlinks, FIFOs and programs')
        except Failure as error:
            self.fail(str(error), error.hint)
        if self.is_pi_arm and self.machine in ('aarch64', 'arm64'):
            page = os.sysconf('SC_PAGE_SIZE')
            if page != 4096:
                self.fail(f'The kernel uses {page // 1024} KiB memory pages; 32-bit ARM programs need 4 KiB',
                          'Raspberry Pi 5 boots kernel_2712.img (16 KiB pages) by default. Add the line\n'
                          '  kernel=kernel8.img\n'
                          'to /boot/firmware/config.txt (as administrator) and reboot.')
            else:
                self.ok('4 KiB kernel pages (needed for 32-bit ARM programs)')
        runs = arm32_runs()
        if self.is_pi_arm:
            if runs:
                self.ok('This kernel runs 32-bit ARM programs')
            elif runs is False:
                self.fail('This kernel cannot run 32-bit ARM programs',
                          'On a Pi 5 use the 4 KiB-page kernel (kernel=kernel8.img in\n'
                          '/boot/firmware/config.txt) with 64-bit Raspberry Pi OS / Debian.')
        elif runs:
            info('32-bit ARM programs run here through emulation (qemu); used only for checks.')
        marker = read_marker(runtime)
        if marker is None:
            self.fail('No assembled runtime yet', 'Run: ./rx3 recover, then ./rx3 assemble')
            return
        if marker.get('state') != 'assembled' or marker.get('firmware') != SUPPORTED_FIRMWARE:
            self.fail('Runtime assembly is incomplete or for a different firmware', 'Run ./rx3 assemble again.')
            return
        self.ok(f"Runtime assembled from RX3 {marker.get('firmware', '?')}")
        missing = [p for p in ['bin/busybox', 'lib/ld-linux.so.3', 'root/pdj/rbp', 'etc/asound.conf',
                               'dev/fb0', 'dev/gpiodrv', 'proc/cpuinfo'] + FIFOS + BIND_FILES + BIND_DIRS
                   if not os.path.lexists(runtime / p)]
        if missing:
            self.fail('Runtime files are missing: ' + ', '.join(missing), 'Repair with: ./rx3 assemble')
        bad = [p for p in FIFOS if os.path.lexists(runtime / p) and
               not stat.S_ISFIFO(os.lstat(runtime / p).st_mode)]
        if bad:
            self.fail('These must be FIFOs: ' + ', '.join(bad), 'Repair with: ./rx3 assemble')
        if 'installed' not in marker:
            self.fail('Patched player and shim not installed yet', 'Run: ./rx3 build, then ./rx3 install')
        else:
            self.ok('Patched player and compatibility shim installed'
                    + (' (6/10/16/25 % tempo ranges)' if marker.get('tempo_range_25') else ''))
            built = self.config.build / 'fbshim.so'
            if built.is_file():
                import hashlib
                if hashlib.sha256(built.read_bytes()).hexdigest() != marker.get('shim_sha256'):
                    self.warn('build/fbshim.so differs from the installed shim',
                              'Run ./rx3 install (with RX3 stopped) to install the newer build.')
        if 'installed' in marker:
            from .safefs import Tree
            import hashlib
            for relative, field in [('root/pdj/rbp-pi', 'player_pi_sha256'), ('lib/fbshim.so', 'shim_sha256')]:
                try:
                    with Tree(runtime) as tree, tree.open_read(relative) as handle:
                        digest = hashlib.sha256(handle.read()).hexdigest()
                    if digest != marker.get(field):
                        self.fail(f'{relative} differs from the installed manifest', 'Run ./rx3 install again.')
                except (OSError, Failure) as error:
                    self.fail(f'{relative}: {error}', 'Run ./rx3 install again.')
        if (runtime / 'lib/ld-linux.so.3').exists():
            self.loader_check(runtime, runs)

    def loader_check(self, runtime, arm32):
        """Libraries resolve (static ELF check); optionally execute inside a rootless chroot."""
        from .elfdeps import missing_libraries
        target = '/root/pdj/rbp-pi' if (runtime / 'root/pdj/rbp-pi').exists() else '/root/pdj/rbp'
        problems = missing_libraries(runtime, target) + missing_libraries(runtime, '/bin/busybox')
        if (runtime / 'lib/fbshim.so').is_file():
            problems += missing_libraries(runtime, '/lib/fbshim.so')
        if problems:
            self.fail("The player's libraries do not all resolve inside the runtime",
                      '\n'.join(problems[:8]) + '\nRepair with: ./rx3 assemble --repair')
        else:
            self.ok('Player, busybox and installed shim libraries resolve inside the runtime')
        if self.is_pi_arm:
            try:
                low = int(Path('/proc/sys/vm/mmap_min_addr').read_text())
            except (OSError, ValueError):
                low = None
            if low is not None and low > 0x8000:
                self.fail(f'vm.mmap_min_addr is {low}; the RX3 1.19 player loads at 32768 and needs <= 32768',
                          'Set it (as administrator) with: sudo sysctl vm.mmap_min_addr=32768\n'
                          'and keep it with a file in /etc/sysctl.d/ containing vm.mmap_min_addr=32768')
            elif low is not None:
                self.ok(f'vm.mmap_min_addr is {low} (the player loads at 32768)')
        if not arm32 or not shutil.which('unshare'):
            return
        try:
            result = subprocess.run(['unshare', '--user', '--map-root-user', '--mount', 'chroot',
                                     str(runtime), '/bin/busybox', 'true'], capture_output=True, timeout=60)
        except (OSError, subprocess.TimeoutExpired) as error:
            info(f'Skipped the test run inside the runtime: {error}')
            return
        if result.returncode == 0:
            self.ok("The runtime's busybox runs inside a rootless test chroot")
        else:
            message = result.stderr.decode(errors='replace').strip().splitlines()
            info('Could not run a program inside the runtime without root '
                 f'({message[-1] if message else "unknown reason"}); ./rx3 start uses sudo instead.')

    def device_checks(self):
        stage('Stage 4 - Raspberry Pi devices for starting RX3')
        if not self.is_pi_arm:
            info('Skipped: these checks only make sense on the Raspberry Pi.')
            return
        config = self.config
        # Display
        cards = detect_drm_cards()
        try:
            drm, how = config.drm_device()
            self.ok(f'Display {drm} ({how})')
            if not os.access(drm, os.R_OK | os.W_OK):
                self.fail(f'No permission to use {drm}', 'Add yourself to the video group:\n'
                          '  sudo usermod -aG video,render $USER   (then log out and back in)')
        except Failure as error:
            self.fail(str(error), error.hint)
        fb = config.get('display', 'fb_device')
        name = Path(fb).name
        try:
            size = Path(f'/sys/class/graphics/{name}/virtual_size').read_text().strip()
            bpp = Path(f'/sys/class/graphics/{name}/bits_per_pixel').read_text().strip()
            if size.split(',')[:2] == [str(PANEL[0]), str(PANEL[1])] and bpp == '32':
                self.ok(f'Framebuffer {fb} is {PANEL[0]}x{PANEL[1]} 32-bit')
            else:
                self.fail(f'Framebuffer {fb} is {size.replace(",", "x")} at {bpp} bits; '
                          f'{PANEL[0]}x{PANEL[1]} 32-bit is required',
                          'Only the 10-inch Raspberry Pi Touch Display 2 (portrait 1200x1920) is supported.')
        except OSError:
            self.fail(f'Framebuffer {fb} not found', 'The display must be connected at boot.')
        if os.path.exists(fb) and not os.access(fb, os.R_OK | os.W_OK):
            self.fail(f'No permission to use {fb}', 'sudo usermod -aG video $USER   (then log in again)')
        if not cards:
            info('No DRM connectors visible under /sys/class/drm')
        desktops = running(DESKTOPS)
        if desktops:
            self.warn('A desktop session is running: ' + ', '.join(sorted({c for _, c in desktops})),
                      'RX3 needs exclusive use of the display. Log out of the desktop, or boot to\n'
                      'the console (sudo raspi-config > System Options > Boot > Console), then start RX3.')
        if not Path(FONT).is_file():
            self.fail(f'Font {FONT} is missing (used by the display helper)',
                      'Install: sudo apt install fonts-dejavu-core', 'fonts-dejavu-core')
        # Touch
        try:
            touch, how = config.touch_device()
            self.ok(f'Touchscreen {touch} ({how})')
            if not os.access(touch, os.R_OK):
                self.fail(f'No permission to read {touch}',
                          'sudo usermod -aG input $USER   (then log out and back in)')
        except Failure as error:
            self.fail(str(error), error.hint)
        # Audio and MIDI
        card = config.get('audio', 'card')
        cards = alsa_cards()
        if card in cards:
            self.ok(f"ALSA card {card}: {cards[card]['description']}")
        else:
            present = ', '.join(cards) or 'none'
            self.fail(f'ALSA card {card} is not connected (present: {present})',
                      'Connect and power on the DDJ-FLX6, or set [audio] card in rx3.conf.')
        if card != 'DDJFLX6':
            self.warn(f'Audio card {card} is untested',
                      'The routing sends master to channels 1/2 and headphones to 3/4 at 44.1 kHz,\n'
                      'as on the DDJ-FLX6. Other interfaces need that 4-channel layout.')
        if not ctypes.util.find_library('asound'):
            self.fail('The ALSA library (libasound.so.2) is missing', 'Install: sudo apt install libasound2',
                      'libasound2')
        if self.tool('amidi', 'alsa-utils', 'finds the controller MIDI port'):
            listing = subprocess.run(['amidi', '-l'], capture_output=True, text=True).stdout
            midi = config.get('controller', 'midi_name')
            if midi in listing:
                self.ok(f'MIDI controller {midi} found')
            else:
                self.fail(f'MIDI controller {midi} not found by amidi -l', 'Connect the controller.')
        servers = running(AUDIO_SERVERS)
        if servers:
            self.warn('Audio servers are running: ' + ', '.join(sorted({c for _, c in servers})),
                      'If the player reports that the audio device is busy, stop the desktop\n'
                      'session (or its sound server) so RX3 can open the controller directly.')
        if running({'mixxx', 'bitedj'}):
            self.warn('Mixxx/BiteDJ is running; stop it before starting RX3 (they share the controller)')
        self.mapping_check()
        self.usb_check()
        for tool, package in (('sudo', 'sudo'), ('chroot', 'coreutils'), ('findmnt', 'util-linux'),
                              ('lsblk', 'util-linux'), ('mount', 'mount')):
            if not shutil.which(tool):
                self.fail(f'{tool} is missing', f'Install: sudo apt install {package}', package)
        if shutil.which('sudo'):
            if subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0:
                self.ok('sudo works without a prompt')
            else:
                info('./rx3 start will ask for your password for the mount/chroot steps.')
        missing_build = [n for n in ('rx3-fb-present', 'rx3-touch-bridge', 'fbshim.so')
                         if not (config.build / n).is_file()]
        if missing_build:
            self.fail('Not built yet: ' + ', '.join(missing_build), 'Run: ./rx3 build')

    def mapping_check(self):
        try:
            mapping = self.config.path('controller', 'mapping')
        except Failure as error:
            self.fail(str(error))
            return
        if not mapping.is_file():
            self.fail(f'Controller mapping not found: {mapping}',
                      'Fetch the pinned mapping with ./rx3 mapping, or use your BiteDJ/Mixxx XML.\n'
                      'Set [controller] mapping in rx3.conf to your Pioneer-DDJ-FLX6.midi.xml.')
            return
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location('flx6_rx3', REPO / 'flx6-rx3.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            bridge = module.Bridge(str(mapping), lambda *a: None)
            self.ok(f'Controller mapping loads: {len(bridge.mapping)} bindings from {mapping}')
        except Exception as error:  # a bad user file must not crash doctor
            self.fail(f'Controller mapping could not be read: {error}')

    def usb_check(self):
        uuid = self.config.get('usb', 'uuid')
        result = subprocess.run(['lsblk', '-J', '-o', 'NAME,FSTYPE,UUID,LABEL,MOUNTPOINTS'],
                                capture_output=True, text=True)
        candidates = []
        if result.returncode == 0:
            import json
            def walk(items):
                for item in items or []:
                    yield item
                    yield from walk(item.get('children'))
            try:
                for item in walk(json.loads(result.stdout).get('blockdevices')):
                    for point in item.get('mountpoints') or []:
                        if point and (Path(point) / 'PIONEER/rekordbox/export.pdb').is_file():
                            candidates.append((item.get('uuid'), item.get('fstype'), point))
            except ValueError:
                pass
        if not uuid:
            info('No music USB configured ([usb] uuid is empty); RX3 will start without media.')
            for found_uuid, fstype, point in candidates:
                info(f'rekordbox USB found: uuid = {found_uuid} ({fstype}, mounted at {point})')
            return
        if not (Path('/dev/disk/by-uuid') / uuid).exists():
            self.warn(f'Music USB {uuid} is not connected')
        else:
            self.ok(f'Music USB {uuid} connected')

    def run(self):
        self.host()
        if 'recover' in self.stages:
            self.recover_checks()
        if 'build' in self.stages:
            self.build_checks()
        stage('Configuration')
        problems = self.config.validate()
        info(f"Settings: {self.config.source or 'built-in defaults (no rx3.conf yet)'}")
        for problem in problems:
            self.fail(problem)
        if not problems:
            self.ok('Configuration is valid')
        if 'runtime' in self.stages and not problems:
            self.runtime_checks()
        if 'devices' in self.stages and not problems:
            self.device_checks()
        stage('Summary')
        if self.packages:
            say('  Install the missing packages with:')
            say('    sudo apt update && sudo apt install ' + ' '.join(self.packages))
        if self.failures:
            say(f'  {self.failures} problem(s), {self.warnings} warning(s). Fix the [FAIL] items above.')
        else:
            say(f'  No blocking problems found ({self.warnings} warning(s)).')
        return 1 if self.failures else 0
