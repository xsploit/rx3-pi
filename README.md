# RX3 on Raspberry Pi

Run the **embedded XDJ-RX3 1.19 player** with compatibility helpers on a Raspberry Pi 5. This is experimental software, not desktop rekordbox and not firmware you flash onto the Pi.

**Start here: use `./rx3` for setup and operation.** It replaces the old sequence of individual Python scripts with a checked recovery → runtime assembly → build → install workflow. You do not need a CDJ/RX3 or a device-specific encryption key. Official inputs are downloaded and verified locally; this repository does not distribute the player, firmware, keys or proprietary libraries.

This branch's installer has passed PC recovery, assembly and cross-build checks. **A fresh installation on a second physical Pi has not been tested.** Earlier playback/touch evidence belongs to the development installation, not acceptance of this new installer.

## Hardware and limits

- Raspberry Pi 5, 4 GB RAM; 64-bit Raspberry Pi OS / Debian with Python 3.9+ and a kernel that runs ARM32 programs. `doctor` checks the kernel.
- The display code currently supports **1200×1920 portrait, 32-bit framebuffer**, presented rotated as 1920×1200 landscape (the project's 10-inch Raspberry Pi Touch Display 2). Other display sizes need code changes, not just a config setting.
- DDJ-FLX6 audio/MIDI. Master uses channels 1/2 and headphones 3/4 at 44.1 kHz. Another audio interface needs the same routing and separate validation; another controller needs a mapping adapter.
- A local Linux filesystem such as ext4 for the runtime. Allow at least **1 GB free**; FAT/exFAT/NTFS cannot hold the runtime's Unix files. Music can be a FAT32 rekordbox-export USB. exFAT is implemented but untested.
- RX3 **1.19 is the supported pin, not the newest-version claim**. The reported newer 1.20 firmware is not supported by these fixed-address patches. Do not substitute another binary.

Windows/x86 PCs can recover and inspect files and run offline tests; playback starts on the Pi. An x86 cross-build produces ARM32 player helpers but x86 display/touch helpers: rebuild on the Pi before launching.

## First setup on the Pi

Run as your normal account, **not `sudo ./rx3`**. Install the prerequisites:

```sh
sudo apt update
sudo apt install git python3 python3-cryptography build-essential pkg-config \
  libdrm-dev libfreetype-dev gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi \
  libc6-dev-armel-cross linux-libc-dev unzip libarchive-tools \
  alsa-utils libasound2 fonts-dejavu-core sudo util-linux mount
```

This setup is currently on the review branch; cloning `main` does not include it:

```sh
git clone --branch opus/human-friendly-setup https://github.com/xsploit/rx3-pi.git
cd rx3-pi
./rx3 config init
./rx3 doctor --stage recover --stage build
```

Fix any `[FAIL]` items, then run:

```sh
./rx3 setup
```

Setup downloads about 322 MB of official ZIPs, recovers the key privately, decrypts/verifies the firmware, creates the complete runtime, compiles the helpers and installs the matching player/shim. It also obtains a pinned public BiteDJ FLX6 XML mapping if the configured file is missing. Existing mapping files are preserved and checked. No Mixxx JavaScript or BiteDJ installation is required for this bridge.

Expected completion: **`Setup finished`**. Important outputs:

| Path | What it contains |
| --- | --- |
| `work/downloads/` | Verified official ZIPs, reused on the next run |
| `work/firmware/aes256.key` | Locally recovered key, owner-readable only |
| `work/firmware/images/` | Verified rootfs, player, GUI and settings archives |
| `work/runtime/` | Assembled Linux runtime with libraries, symlinks and emulated devices |
| `work/runtime/root/pdj/rbp-pi` | Patched 1.19 player |
| `work/runtime/lib/fbshim.so` | Matching ARM32 compatibility shim |
| `build/` | Compiled display/touch helpers and test programs |
| `work/state/logs/` | Startup logs, created when you start |

**Already extracted a key or `rx3.tar.bz2` using the old script?** You can leave those files alone. Run `./rx3 setup --from /path/to/folder-containing-original-zips`. It recognizes the three original ZIPs by size and SHA-256, regardless of filename, and performs the remaining steps in the correct order. It does not import an arbitrary key/player or guess which partial files are valid. If you only have the joined tarball, run `./rx3 setup`; it downloads the required original ZIPs.

To prepare without networking later, run `./rx3 mapping` once, retain the three ZIPs, then use `./rx3 setup --offline --from /path/to/zips`. The pinned URLs and checksums are in [rx3tool/recover.py](rx3tool/recover.py); the mapping URL/checksum is in [rx3tool/mapping.py](rx3tool/mapping.py). Official upstream pages: [source packages](https://www.pioneerdj.com/en/support/open-source-code-distribution/gnu-open-source-license/) and [RX3 firmware](https://support.alphatheta.com/en-US/articles/4562999179673). If upstream removes the pinned download, the tool stops with instructions rather than substituting a different version.

## Configure music, then start

Find your USB UUID:

```sh
lsblk -o NAME,FSTYPE,UUID,LABEL,MOUNTPOINTS
```

Edit `rx3.conf` and put the music partition's UUID in `[usb]`:

```ini
[usb]
uuid = 1234-ABCD
```

Leave it empty to boot without music. Use a rekordbox USB export containing `PIONEER/rekordbox/export.pdb`; copying loose tracks is not a tested library workflow.

```sh
./rx3 doctor
./rx3 start --dry-run
./rx3 start
./rx3 status
```

`doctor` reports the detected display/touch devices, access permissions, audio/MIDI, kernel and runtime. Fix its `[FAIL]` items before starting. The launcher prints privileged commands and asks for your sudo password for mounts/chroot. Use a local text console with the desktop logged out so RX3 can own the display. Close BiteDJ/Mixxx first so they release the controller.

To stop and release the devices/mounts:

```sh
./rx3 stop
```

The USB is mounted **read-only inside the RX3 runtime**. Database/analysis files are copied to `work/runtime/media/usb2/sdb1`, preserving local cue/grid edits on later starts. Music stays on the USB; the supported music folders are `Contents`, `Music` and `PIONEER/Artwork`. This does not write edits back to the original USB. Changing USB UUID requires a separate runtime to avoid mixing two databases. Re-exporting the same USB does not automatically refresh existing local database/analysis files; keep the existing runtime as an edits backup and build a new runtime for a refreshed export.

## Settings and individual steps

Everything in the supported startup path uses [rx3.conf.example](rx3.conf.example). Defaults detect your account/groups and display/touch device; USB identity is yours to set. Device ambiguity is an error, not a guessed selection.

```sh
./rx3 config show
./rx3 --set usb.uuid=1234-ABCD start
./rx3 --config /path/to/another.conf doctor
```

Relative paths are relative to the configuration file's folder, including paths containing spaces. Precedence: defaults → config file → `RX3_SECTION_KEY` environment → `--set section.key=value`. Changing `[paths] work` changes recovery/download storage only; runtime, state, build and controller mapping are separate paths. Keep them in dedicated directories outside another installation.

For an existing preferred BiteDJ mapping, set `[controller] mapping` to its XML path and run `./rx3 mapping --offline`. This bridge translates supported XML bindings; it does not execute the XML's referenced Mixxx JavaScript.

If you prefer to inspect each stage:

```sh
./rx3 mapping
./rx3 recover
./rx3 assemble
./rx3 build
./rx3 install
./rx3 validate
```

Recovery reuses verified files and resumes partial downloads. Assembly recognizes interrupted attempts and keeps player-written settings/local library files. `assemble --repair` rewrites firmware files, including factory settings; back up any custom settings first. Build/install require the player stopped. Install keeps changed previous player/shim copies as `.previous` and records hashes so validation catches an interrupted or mismatched installation. After changing the audio card, repeat assemble → build → install.

`./rx3 setup --dry-run` prints the plan without downloading, building, mounting or starting. `./rx3 selftest` runs offline synthetic, replay and C tests; it needs the Python/build dependencies but no firmware or Pi. Every command has `--help`.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| `xf86drm.h: No such file or directory` in `drm-present.h` / `test-frame-exchange` | Install `libdrm-dev pkg-config libfreetype-dev`, then run `./rx3 build`. The build supplies the required pkg-config include flags; don't compile that test without them. |
| `arm-linux-gnueabi-gcc` or ARM headers missing | Install `gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi libc6-dev-armel-cross linux-libc-dev`, then `./rx3 doctor --stage build`. |
| Recovery says `Killed`, or stopped after key recovery | Run the same command again. `journalctl -k -b` can show an OOM kill; `Killed` alone does not establish why. Recovery streams the source archive and avoids holding the whole firmware in memory. |
| Only `extracted/rx3.tar.bz2` exists | That's an intermediate output from the old script, not a runnable installation. Use `./rx3 setup --from /folder/with/original/zips`. |
| Key exists, but no player/runtime | `./rx3 setup` does the remaining stages. A key alone is not sufficient; don't run random research scripts. |
| 16 KiB kernel pages / ARM32 execution fails | Follow `doctor`'s Pi kernel guidance: select `kernel=kernel8.img` in `/boot/firmware/config.txt`, reboot, and check again. The player requires ARM32 support and 4 KiB pages. |
| `vm.mmap_min_addr` blocks the player | `doctor` explains the required value (32768 or lower) and the sysctl change. The tool does not change system settings automatically. |
| Device permission denied | Follow `doctor`'s group guidance (`audio`, `video`, `render`, `input` as applicable), then log out/in. Never run the whole setup as root to work around this. |
| No display / unsupported geometry | `./rx3 doctor`; this presenter requires 1200×1920 portrait 32-bit. Configure the detected DRM card/touch event path only if auto-detection is ambiguous. |
| Player or helper exits | Read `work/state/logs/player.log`, `display.log`, `touch.log`, `midi.log`. Run `./rx3 stop` to release any partial startup before retrying. |
| Music USB already mounted without UTF-8 | Unmount it in the desktop without unplugging, then retry; the launcher mounts it with the expected options. |
| Another runtime or unexplained process owns devices | Stop that installation using its own launcher. This tool scopes stop actions to the configured runtime and refuses to kill a player it cannot identify. |

## Existing installations and development notes

Create a **new empty runtime directory** for this setup; don't point it at your hand-assembled rootfs. No automatic migration is attempted. Keep the old installation and its library/settings as a backup, and stop it using its original launcher before trying the new one. Do not run both at once.

`recover-firmware.py`, `start-rx3.sh` and `stop-rx3.sh` are compatibility entry points to the new CLI. Other legacy experiments such as `prepare-runtime.py` and `prepare-library-view.sh` **are not part of this install path** and may retain historical machine assumptions. The complete old research README is preserved in [DEVELOPMENT-CHECKPOINT.md](DEVELOPMENT-CHECKPOINT.md); [VALIDATION.md](VALIDATION.md) records prior development evidence. Neither replaces the setup instructions above.

## What still needs physical testing

The development installation demonstrated browsing/loading, playback through FLX6 headphones, stacked waveforms and several touch/mixer controls. Waveform flicker and native animation cadence remain unresolved. This setup work does not claim a performance upgrade, universal controller support, all FX/pad/LED behavior, or perfect native touchscreen parity.

Before relying on this branch, a volunteer must test a fresh Pi boot, physical display/touch alignment, both decks' play/cue/load, browse/back/view, mixer/master/headphone routing, music mounting, stop/restart and unplug/reconnect. [Setup validation](docs/SETUP-VALIDATION.md) distinguishes the offline checks from that remaining hardware acceptance.
