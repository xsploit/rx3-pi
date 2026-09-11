"""Fetch a pinned public BiteDJ FLX6 mapping, or validate a user-supplied XML."""
import hashlib
import importlib.util
import urllib.request
from . import REPO
from .safefs import Tree
from .ui import Failure, ok, say

URL = ('https://raw.githubusercontent.com/xsploit/bitedj/'
       'ee55091a697c1c3f18a07920098eb613f2ccd1d7/res/controllers/Pioneer-DDJ-FLX6.midi.xml')
SHA256 = 'e58ec496995c3203f7d5d35de7cdcd24dc553e880912e669faf8b9c1e456444b'


def ensure(config, offline=False, dry_run=False):
    target = config.path('controller', 'mapping')
    if not target.exists():
        if offline:
            raise Failure(f'Controller mapping missing: {target}',
                          'Run ./rx3 mapping with network access, or set [controller] mapping to your XML.')
        if dry_run:
            say(f'  [dry-run] would fetch {URL} to {target}')
            return
        with urllib.request.urlopen(URL, timeout=30) as response:
            data = response.read(1024 * 1024)
        if hashlib.sha256(data).hexdigest() != SHA256:
            raise Failure('Downloaded controller mapping checksum does not match; nothing installed')
        with Tree(target.parent, create=True) as tree:
            tree.write(target.name, data, 0o644, replace=False)
    spec = importlib.util.spec_from_file_location('rx3_mapping_check', REPO / 'flx6-rx3.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        bridge = module.Bridge(str(target), lambda *a: None)
    except Exception as error:
        raise Failure(f'Cannot load controller mapping {target}: {error}')
    if not bridge.mapping:
        raise Failure(f'No supported FLX6 bindings found in {target}')
    ok(f'Controller mapping: {len(bridge.mapping)} bindings from {target}')
