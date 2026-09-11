#!/usr/bin/env python3
"""Compatibility name for ./rx3 recover (recover RX3 1.19 from official downloads).

Outputs now go to work/firmware/ (see ./rx3 recover --help); nothing is flashed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from rx3tool.cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main(['recover'] + sys.argv[1:]))
