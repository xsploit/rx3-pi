# Human setup validation — 2026-09-11

This validates the `./rx3` setup path on Linux x86_64. It does **not** certify a fresh physical Raspberry Pi installation. The Pi remained off throughout this work.

## Checks performed

- Fresh copy of tracked source plus proposed changes in a directory named `clean checkout with spaces`; no existing runtime or private key was imported.
- `config init` and pinned public FLX6 mapping fetch: 126 translated bindings.
- Recovery from the three original official ZIPs, each checked against the pinned SHA-256; local key recovery, firmware decryption, ISO and all extracted image hashes checked.
- Runtime assembly twice: second run retained the runtime, with firmware symlinks and emulated devices present.
- Native display/touch helpers and ARM32 shim/clock stub compiled. ARM cross tools were Debian Bookworm GCC 12/binutils unpacked into a private test directory, not installed system-wide. Python cryptography was in an isolated environment.
- Player patched from verified original 1.19 bytes; matching shim installed; manifest validation and static ELF dependency checks passed.
- `selftest`: 21 Python unit tests, seven replay suites and nine compiled C tests. Covers cipher streaming, truncated streams, configuration precedence/path spaces, missing dependencies, archive traversal, symlink writes, interrupted assembly recognition, unknown runtime preservation, read-only dry-run behavior, process scoping, delayed startup, USB identity changes, mapping checksum failure and download restart when a server ignores Range.
- The frame-exchange stress test originally required an accepted frame during a racing writer's run, even though rejecting all unstable snapshots is correct. It now also checks every pixel of the final quiescent frame and does not require a particular scheduling interleaving. The mixed-frame checks during contention remain.
- Clean `setup --dry-run` and idempotent `setup --offline` checked. No sudo, physical devices, music, host package installation or Pi access was used.

The ARM execution probe/rootless busybox check may use a host's existing QEMU support. Static checks and cross compilation do not establish that the player, graphics, input or sound works on the target hardware.

## Required physical acceptance

On a separately prepared supported Pi, follow README from a fresh checkout, then verify:

1. Kernel/device doctor checks; cold boot and successful launch without manual path edits.
2. Landscape display and physical touch alignment, browse/back/view and both deck loads.
3. Both decks' master and headphone cue output, faders/EQ/filter/crossfader, play/pause/cue, jog and tempo behavior.
4. Correct library from the configured USB; edits preserved locally across restart; no writes through the runtime's original USB mount.
5. Stop releases the controller/display; start restores them; logs identify failures.
6. Physical MIDI/audio unplug/reconnect, waveform flicker/cadence, remaining pad/FX/LED behavior.

Do not mark these complete from screenshots, build success or prior development evidence.
