#!/usr/bin/env python3
"""Research helper: extract a cramfs image into a folder and record its symlinks.

Usage: extract_cramfs.py [IMAGE] [DESTINATION]
Defaults: work/firmware/images/rootfs.cramfs -> work/firmware/runtime-files.
This is NOT the setup path: ./rx3 assemble builds the complete runtime.
"""
import json
import sys
from pathlib import Path

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base))
from rx3tool.cramfs import extract  # noqa: E402
from rx3tool.safefs import Tree  # noqa: E402
from rx3tool.ui import Failure  # noqa: E402

args = sys.argv[1:]
if len(args) > 2 or (args and args[0] in ('-h', '--help')):
    sys.exit(__doc__)
image = Path(args[0]) if args else base / 'work/firmware/images/rootfs.cramfs'
target = Path(args[1]) if len(args) > 1 else base / 'work/firmware/runtime-files'
try:
    with Tree(target, create=True) as tree:
        stats, links = extract(image, tree)
except (Failure, OSError) as error:
    sys.exit(f'extract_cramfs.py: {error}')
(target.parent / 'runtime-symlinks.json').write_text(json.dumps(links, indent=2))
print(f"Extracted {stats['files']} regular files; recorded {len(links)} symlinks; "
      f"skipped {stats['special']} device nodes.")
