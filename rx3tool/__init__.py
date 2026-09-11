"""Setup, validation and launch helpers for running the RX3 player on a Pi.

Standard library only, so the tool works before any Python package is
installed. Firmware decryption additionally needs `cryptography`.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# firmware_image.py and the patch scripts live at the top of the checkout.
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
