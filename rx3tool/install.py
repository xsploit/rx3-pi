"""Install the patched player and the matching compatibility shim into the runtime.

The two files are a pair: the shim hooks fixed addresses of the patched 1.19
player. Each is replaced atomically, only while the player is stopped, and the
previous versions are kept as `.previous` for rollback.
"""
import hashlib
import importlib.util
import json
import time

from . import REPO
from .assemble import MARKER, read_marker, write_marker
from .safefs import Tree
from .system import player_pids
from .ui import Failure, info, ok, say, stage

PLAYER = 'root/pdj/rbp-pi'
SHIM = 'lib/fbshim.so'


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), REPO / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def build_player(runtime, clock, tempo25):
    patcher = load_script('patch-player')
    with Tree(runtime) as tree, tree.open_read('root/pdj/rbp') as handle:
        original = handle.read()
    try:
        data = patcher.patched(original, clock)
        if tempo25:
            data = load_script('patch-tempo25').patched(data)
    except ValueError as error:
        raise Failure(f'Cannot patch the player: {error}')
    return data


class Installer:
    def __init__(self, config, dry_run=False):
        self.config = config
        self.dry_run = dry_run
        self.runtime = config.runtime
        self.build = config.build

    def run(self):
        say(f'Installing the patched player and compatibility shim into {self.runtime}')
        marker = read_marker(self.runtime)
        if marker is None or marker.get('state') != 'assembled':
            raise Failure(f'{self.runtime} is not an assembled runtime', 'Run ./rx3 assemble first.')
        shim = self.build / 'fbshim.so'
        clock = self.build / 'pi-clock.bin'
        missing = [str(p) for p in (shim, clock) if not p.is_file()]
        if missing:
            raise Failure('Build outputs are missing: ' + ', '.join(missing), 'Run ./rx3 build first.')
        if player_pids(self.runtime):
            raise Failure('The RX3 player is running; its files cannot be replaced now',
                          'Stop it first: ./rx3 stop')
        tempo25 = self.config.flag('firmware', 'tempo_range_25')
        player = build_player(self.runtime, clock.read_bytes(), tempo25)
        shim_data = shim.read_bytes()
        if len(shim_data) < 52 or not shim_data.startswith(b'\x7fELF\x01\x01\x01') or shim_data[18:20] != b'\x28\x00':
            raise Failure(f'{shim} is not a 32-bit ARM shared library', 'Rebuild with ./rx3 build.')
        variant = '6/10/16/25 % tempo ranges' if tempo25 else 'original 6/10/16/WIDE tempo ranges'
        if self.dry_run:
            say(f'  [dry-run] would write {PLAYER} ({variant}) and {SHIM}; previous copies kept as .previous')
            return
        with Tree(self.runtime) as tree:
            for relative, data, mode in ((PLAYER, player, 0o755), (SHIM, shim_data, 0o755)):
                current = tree.lstat(relative)
                if current is not None:
                    with tree.open_read(relative) as handle:
                        old = handle.read()
                    if old == data:
                        ok(f'{relative} already up to date')
                        continue
                    tree.write(relative + '.previous', old, 0o644)
                tree.write(relative, data, mode)
                ok(f'Installed {relative}')
        marker.update({'installed': time.time(), 'player_pi_sha256': sha256(player),
                       'shim_sha256': sha256(shim_data), 'tempo_range_25': tempo25})
        write_marker(self.runtime, marker)
        stage('Installed')
        info(f'Player: RX3 1.19 with Pi patches, {variant}')
        say('\nNext steps: ./rx3 validate   then   ./rx3 start')
