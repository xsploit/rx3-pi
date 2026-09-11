"""Load `rx3.conf`, apply overrides, detect `auto` values and validate them.

Precedence (later wins): built-in defaults, the config file, environment
variables `RX3_<SECTION>_<KEY>`, then `--set section.key=value` options.
Relative paths are relative to the directory containing the config file (the
checkout by default), so a checkout path with spaces works unchanged.
"""
import configparser
import grp
import os
import pwd
import re
from pathlib import Path

from . import REPO
from .ui import Failure

SUPPORTED_FIRMWARE = '1.19'
NEWER_FIRMWARE_NOTE = (
    'The supported pin is RX3 firmware 1.19, not a claim about the latest release, '
    'but it is not supported here: the player patches and the compatibility shim use fixed code '
    'addresses verified only for 1.19. Nothing is installed on any DJ hardware: the 1.19 player '
    'only runs inside the Pi runtime, so no XDJ-RX3 or firmware update is involved.')
PANEL = (1200, 1920)

DEFAULTS = {
    'paths': {
        'work': 'work',
        'runtime': 'work/runtime',
        'state': 'work/state',
        'build': 'build',
    },
    'firmware': {
        'version': SUPPORTED_FIRMWARE,
        'tempo_range_25': 'yes',
    },
    'user': {
        'uid': 'auto',
        'gid': 'auto',
        'groups': 'auto',
    },
    'display': {
        'drm_device': 'auto',
        'fb_device': '/dev/fb0',
    },
    'touch': {
        'device': 'auto',
    },
    'audio': {
        'card': 'DDJFLX6',
    },
    'controller': {
        'midi_name': 'DDJ-FLX6',
        'mapping': 'work/Pioneer-DDJ-FLX6.midi.xml',
    },
    'usb': {
        'uuid': '',
    },
}

ALSA_ID = re.compile(r'^[A-Za-z0-9_]{1,15}$')
UUID = re.compile(r'^[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}$|^[0-9A-Fa-f-]{8,36}$')
TRUE = {'1', 'yes', 'true', 'on'}
FALSE = {'0', 'no', 'false', 'off'}


class Config:
    def __init__(self, values, base, source):
        self.values = values
        self.base = base
        self.source = source
        self.origin = {}
        self._detected = {}

    # -- raw values ---------------------------------------------------------
    def get(self, section, key):
        return self.values[section][key].strip()

    def path(self, section, key):
        text = self.get(section, key)
        if not text:
            raise Failure(f'[{section}] {key} must not be empty')
        if '\n' in text or '\0' in text:
            raise Failure(f'[{section}] {key} contains an invalid character')
        path = Path(os.path.expanduser(text))
        if not path.is_absolute():
            path = self.base / path
        return Path(os.path.normpath(path))

    def flag(self, section, key):
        text = self.get(section, key).lower()
        if text in TRUE:
            return True
        if text in FALSE:
            return False
        raise Failure(f'[{section}] {key} must be yes or no, not {text!r}')

    # -- common derived paths ----------------------------------------------
    @property
    def work(self):
        return self.path('paths', 'work')

    @property
    def runtime(self):
        return self.path('paths', 'runtime')

    @property
    def state(self):
        return self.path('paths', 'state')

    @property
    def build(self):
        return self.path('paths', 'build')

    @property
    def downloads(self):
        return self.work / 'downloads'

    @property
    def firmware_dir(self):
        return self.work / 'firmware'

    # -- validation -------------------------------------------------------
    def validate(self):
        """Check syntax and unsupported combinations; never touches devices."""
        problems = []

        def check(fn):
            try:
                fn()
            except Failure as error:
                problems.append(str(error))

        version = self.get('firmware', 'version')
        if version != SUPPORTED_FIRMWARE:
            problems.append(f'[firmware] version = {version!r} is not supported; only '
                            f'{SUPPORTED_FIRMWARE} is. {NEWER_FIRMWARE_NOTE}')
        check(lambda: self.flag('firmware', 'tempo_range_25'))
        for key in ('work', 'runtime', 'state', 'build'):
            check(lambda key=key: self.path('paths', key))
        try:
            runtime = self.runtime.resolve()
            forbidden = [Path('/'), Path('/dev'), Path('/proc'), Path('/sys'), Path('/etc'),
                         Path('/usr'), Path('/boot'), Path('/home'), Path.home()]
            if runtime in forbidden or any(runtime == p or p in runtime.parents
                                           for p in (Path('/dev'), Path('/proc'), Path('/sys'))):
                problems.append(f'[paths] runtime = {runtime} is not allowed; use a dedicated '
                                'directory such as work/runtime or ~/rx3-runtime')
            if runtime == REPO or runtime in REPO.parents:
                problems.append('[paths] runtime must not be the checkout itself or one of its parents')
        except Failure:
            pass
        for key in ('uid', 'gid'):
            value = self.get('user', key)
            if value != 'auto':
                if not value.isdigit():
                    problems.append(f'[user] {key} must be auto or a number, not {value!r}')
                elif key == 'uid' and int(value) == 0:
                    problems.append('[user] uid = 0 is not allowed: the player must not run as root')
        groups = self.get('user', 'groups')
        if groups != 'auto':
            for item in filter(None, (g.strip() for g in groups.split(','))):
                if not item.isdigit():
                    try:
                        grp.getgrnam(item)
                    except KeyError:
                        problems.append(f'[user] groups: unknown group {item!r}')
        for key, prefix in (('drm_device', '/dev/dri/'), ('fb_device', '/dev/fb')):
            value = self.get('display', key)
            if value != 'auto' and not value.startswith(prefix):
                problems.append(f'[display] {key} must be auto or a path starting with {prefix}')
        touch = self.get('touch', 'device')
        if touch != 'auto' and not touch.startswith('/dev/input/'):
            problems.append('[touch] device must be auto or a path under /dev/input/')
        card = self.get('audio', 'card')
        if not ALSA_ID.match(card):
            problems.append(f'[audio] card must be an ALSA card ID (letters, digits, _; max 15), '
                            f'not {card!r}. See: cat /proc/asound/cards')
        name = self.get('controller', 'midi_name')
        if not name or not name.isprintable():
            problems.append('[controller] midi_name must be printable text')
        check(lambda: self.path('controller', 'mapping'))
        uuid = self.get('usb', 'uuid')
        if uuid and not UUID.match(uuid):
            problems.append(f'[usb] uuid {uuid!r} does not look like a filesystem UUID. '
                            'See: lsblk -o NAME,FSTYPE,UUID,MOUNTPOINTS')
        return problems

    def require_valid(self):
        problems = self.validate()
        if problems:
            where = self.source if self.source else 'built-in defaults'
            raise Failure('Configuration problems (' + str(where) + '):\n  - ' + '\n  - '.join(problems))

    # -- user identity ------------------------------------------------------
    def invoking_user(self):
        """The person running the tool, even when started through sudo."""
        uid = os.environ.get('SUDO_UID') if os.geteuid() == 0 else None
        return int(uid) if uid else os.getuid()

    def uid(self):
        value = self.get('user', 'uid')
        return self.invoking_user() if value == 'auto' else int(value)

    def gid(self):
        value = self.get('user', 'gid')
        if value != 'auto':
            return int(value)
        try:
            return pwd.getpwuid(self.uid()).pw_gid
        except KeyError:
            return os.getgid()

    def groups(self):
        value = self.get('user', 'groups')
        if value == 'auto':
            try:
                name = pwd.getpwuid(self.uid()).pw_name
                found = os.getgrouplist(name, self.gid())
            except KeyError:
                found = os.getgroups()
            return sorted(set(found) - {self.gid()})
        result = []
        for item in filter(None, (g.strip() for g in value.split(','))):
            result.append(int(item) if item.isdigit() else grp.getgrnam(item).gr_gid)
        return result

    # -- hardware detection (read-only) ------------------------------------
    def drm_device(self):
        value = self.get('display', 'drm_device')
        if value != 'auto':
            return value, 'configured'
        cards = detect_drm_cards()
        panel = [c for c in cards if c['panel']]
        if len(panel) == 1:
            return panel[0]['device'], f"auto: {panel[0]['connector']} reports {PANEL[0]}x{PANEL[1]}"
        if len(panel) > 1:
            raise Failure('More than one connected 1200x1920 display found; set [display] drm_device',
                          '\n'.join(c['device'] + ' ' + c['connector'] for c in panel))
        connected = [c for c in cards if c['connected']]
        if connected:
            modes = ', '.join(f"{c['connector']}: {c['modes'][:3]}" for c in connected)
            raise Failure(f'No connected display reports the supported {PANEL[0]}x{PANEL[1]} portrait mode',
                          f'Found {modes}. Only the 10-inch Raspberry Pi Touch Display 2 geometry is supported.')
        raise Failure('No connected DRM display found under /sys/class/drm',
                      'Connect the display and boot with it attached, then run ./rx3 doctor again.')

    def touch_device(self):
        value = self.get('touch', 'device')
        if value != 'auto':
            return value, 'configured'
        found = detect_touchscreens()
        if len(found) == 1:
            return found[0]['device'], f"auto: {found[0]['name']}"
        if not found:
            raise Failure('No multi-touch input device found',
                          'Check the display ribbon/touch connection, then run: ls -l /dev/input/by-path')
        listing = '\n'.join(f"{t['device']}  ({t['name']})" for t in found)
        raise Failure('More than one touchscreen found; choose one with [touch] device in rx3.conf', listing)

    def env(self):
        """Environment for helpers that locate the runtime's shared files."""
        return {'RX3_RUNTIME': str(self.runtime)}


def load(path=None, overrides=(), env=None, allow_missing=False):
    env = os.environ if env is None else env
    explicit = path is not None or 'RX3_CONFIG' in env
    if path is None:
        path = env.get('RX3_CONFIG') or (REPO / 'rx3.conf')
    path = Path(path).expanduser()
    values = {s: dict(keys) for s, keys in DEFAULTS.items()}
    origin = {(s, k): 'default' for s, keys in DEFAULTS.items() for k in keys}
    source = None
    if path.exists():
        if not path.is_file():
            raise Failure(f'Configuration path is not a file: {path}')
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str.lower
        try:
            with path.open(encoding='utf-8') as handle:
                parser.read_file(handle)
        except (configparser.Error, UnicodeDecodeError) as error:
            raise Failure(f'Cannot read {path}: {error}')
        for section in parser.sections():
            if section not in DEFAULTS:
                raise Failure(f'Unknown section [{section}] in {path}',
                              'Valid sections: ' + ', '.join(DEFAULTS))
            for key, value in parser[section].items():
                if key not in DEFAULTS[section]:
                    raise Failure(f'Unknown setting [{section}] {key} in {path}',
                                  'Valid settings: ' + ', '.join(DEFAULTS[section]))
                values[section][key] = value
                origin[(section, key)] = 'file'
        source = path
    elif explicit and not allow_missing:
        raise Failure(f'Configuration file not found: {path}',
                      'Create one with: ./rx3 config init')
    for section, keys in DEFAULTS.items():
        for key in keys:
            name = f'RX3_{section.upper()}_{key.upper()}'
            if name in env:
                values[section][key] = env[name]
                origin[(section, key)] = f'environment {name}'
    for item in overrides:
        name, sep, value = item.partition('=')
        section, dot, key = name.strip().partition('.')
        if not sep or not dot or section not in DEFAULTS or key not in DEFAULTS[section]:
            raise Failure(f'Invalid --set {item!r}; use section.key=value, for example '
                          '--set usb.uuid=1234-ABCD')
        values[section][key] = value
        origin[(section, key)] = '--set'
    if explicit and allow_missing:
        source = path
    config = Config(values, (path.parent if source else REPO).resolve(), source)
    config.origin = origin
    return config


# -- detection helpers (pure reads of /sys and /proc) ---------------------

def detect_drm_cards(sys_root='/sys/class/drm'):
    cards = []
    root = Path(sys_root)
    if not root.is_dir():
        return cards
    for connector in sorted(root.glob('card*-*')):
        card = connector.name.split('-', 1)[0]
        try:
            status = (connector / 'status').read_text().strip()
            modes = (connector / 'modes').read_text().split()
        except OSError:
            continue
        connected = status == 'connected'
        cards.append({'device': f'/dev/dri/{card}', 'connector': connector.name,
                      'connected': connected, 'modes': modes,
                      'panel': connected and f'{PANEL[0]}x{PANEL[1]}' in modes})
    return cards


ABS_MT_POSITION_X = 0x35


def _has_abs_bit(text, bit):
    words = text.split()
    if not words:
        return False
    value = 0
    for word in words:
        value = (value << 64) | int(word, 16)
    return bool(value >> bit & 1)


def detect_touchscreens(sys_root='/sys/class/input', dev_root='/dev/input'):
    found = []
    for event in sorted(Path(sys_root).glob('event*')):
        try:
            caps = (event / 'device/capabilities/abs').read_text()
            name = (event / 'device/name').read_text().strip()
        except OSError:
            continue
        if not _has_abs_bit(caps, ABS_MT_POSITION_X):
            continue
        device = f'{dev_root}/{event.name}'
        by_path = Path(dev_root) / 'by-path'
        if by_path.is_dir():
            for link in sorted(by_path.iterdir()):
                try:
                    if os.path.realpath(link) == os.path.realpath(device):
                        device = str(link)
                        break
                except OSError:
                    continue
        found.append({'device': device, 'name': name})
    return found


def alsa_cards(path='/proc/asound/cards'):
    cards = {}
    try:
        text = Path(path).read_text()
    except OSError:
        return cards
    for match in re.finditer(r'^\s*(\d+)\s+\[(\S+)\s*\]:\s*(.*)$', text, re.M):
        cards[match[2]] = {'index': int(match[1]), 'description': match[3].strip()}
    return cards


def render_example():
    return (REPO / 'rx3.conf.example').read_text(encoding='utf-8')
