#!/usr/bin/env python3
"""Create rbp-pi from the verified RX3 1.19 rbp and the ARM clock stub.

Usage: patch-player.py [ORIGINAL_RBP] [PI_CLOCK_BIN] [OUTPUT]
Defaults keep the original layout: pi-runtime/rbp, pi-clock.bin, rbp-pi.
`./rx3 install` calls patched() directly; the input is never modified.
"""
from pathlib import Path
import hashlib
import struct
import sys

PLAYER_SHA256 = '60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09'
# The stub replaces user_space_rtc_init (0x4234c-0x423cb), which is no longer called.
CLOCK_LIMIT = 0x423cc - 0x4234c


def patched(original, clock):
    if hashlib.sha256(original).hexdigest() != PLAYER_SHA256:
        raise ValueError('Input is not the original RX3 1.19 rbp; patch addresses would be wrong')
    if not clock or len(clock) > CLOCK_LIMIT or len(clock) % 4:
        raise ValueError('pi-clock.bin has an unexpected size; rebuild it with build.sh')
    p = bytearray(original)
    def patch(a, v): p[a-0x8000:a-0x8000+len(v)] = v
    def words(a, *v): patch(a, struct.pack('<'+'I'*len(v), *v))
    def branch(a, b, link=False): return (0xeb000000 if link else 0xea000000)|(((b-a-8)//4)&0xffffff)
    words(0x10284, 0xe320f000)
    patch(0x4234c, clock)
    words(0x42318, branch(0x42318, 0x4234c))
    words(0x42330, 0xe92d4010, branch(0x42334, 0x4234c, True), 0xe300314d, 0xe0810390, 0xe8bd8010)
    patch(0x443454, b'debug\0')
    words(0x1a3ab8, 0xe3003c03)
    words(0x1a3ac0, 0xe3403040)
    # Original GPIO interrupts do not exist on the Pi; retain emulated initial states.
    words(0x28ac8, 0xe12fff1e)
    # Select the existing audio profile; PCM devices are redirected by fbshim.
    words(0x3c6654, 0xe3a00001)
    return bytes(p)


if __name__ == '__main__':
    b = Path(__file__).parent
    args = [Path(a) for a in sys.argv[1:]]
    if len(args) not in (0, 3):
        sys.exit(__doc__)
    source, clock, output = args or (b/'pi-runtime/rbp', b/'pi-clock.bin', b/'rbp-pi')
    try:
        result = patched(source.read_bytes(), clock.read_bytes())
    except (OSError, ValueError) as error:
        sys.exit(f'patch-player.py: {error}')
    output.write_bytes(result)
    output.chmod(0o755)
    print(f'Created {output}')
