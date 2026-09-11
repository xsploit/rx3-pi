# RX3 on Raspberry Pi — development checkpoint

Experimental compatibility work running the ARM32 RX3 v1.19 player on Raspberry Pi 5 (4GB), Debian, Raspberry Pi Touch Display 2, and DDJ-FLX6. This is the embedded RX3 application, not desktop rekordbox.

**Read this before following the build commands:** this repository preserves one
working development setup. It is not a portable installer. Several scripts and
compiled helpers still contain the original owner's username, paths, display
geometry, USB identity, Linux group IDs and FLX6 routing. A successful firmware
recovery or build does not create a runnable installation on another Pi.

## Using this on a different machine

There are three separate stages:

1. **Recover the firmware files.** `recover-firmware.py` uses paths relative to
   its own repository directory. It can recover the source-package key and
   verified original player without the owner's account, controller or USB.
   See [Firmware inputs](#firmware-inputs). The key is `aes256.key` beside the
   script; the player is `extracted/player/pdj/rbp`.
2. **Build the compatibility tools.** Install the development packages listed
   below. Standalone tests such as `test-frame-exchange` can run without a
   prepared firmware runtime. The full ARM32 shim links against libraries in
   a prepared RX3 rootfs; give `build.sh` that directory explicitly.
3. **Assemble and adapt the runtime.** This is still manual and incomplete as
   a documented fresh-machine procedure. Extracted files are not equivalent
   to the prepared chroot. The runtime also needs the patched player, matching
   shim, libraries and symlinks, emulated device/proc files, FIFOs, permissions,
   mounts and library views. `prepare-runtime.py` restores mounts for an
   **existing** runtime; it does not construct one. `extract_cramfs.py` extracts
   regular files and records symlink information; it is not a chroot installer.

### Settings still tied to the original Pi

There is currently no central configuration file. These are the principal
runtime assumptions found in the checked-in source, not an exhaustive promise
that every experiment or test is portable:

| Area | Current assumption | Files to adapt |
| --- | --- | --- |
| Host account and rootfs | `/home/pompu_5`, `/home/pompu_5/rx3-rootfs`; helpers deployed directly into that home | `start-rx3.sh`, `stop-rx3.sh`, `prepare-runtime.py`, `prepare-library-view.sh`, `pi-control.py`, `pi-controls.h`, `fb-present.c` |
| Build rootfs | Defaults to the owner's rootfs; ARM32 compiler defaults to `arm-linux-gnueabi-gcc` | Pass `sh build.sh /absolute/path/to/prepared-rootfs`; `build-audio-candidate.sh` also accepts that path and `CC_ARM` |
| Linux permissions | Chroot user/group `1000:44`, supplementary groups `29,44,995,991`; USB mount owner `1000:1000`; mount/start commands use `sudo -n` | `start-rx3.sh`, `prepare-runtime.py`; use your actual IDs and device permissions |
| USB source | Filesystem UUID `0FFF-3865`, fallback filesystem type `vfat` | `USB_UUID` and mount handling in `prepare-runtime.py`; another filesystem needs compatible handling |
| Display | Host `/dev/fb0`, DRM `/dev/dri/card0`, physical 1200×1920 portrait mode, rotated 1920×1200 presentation | `drm-present.h`, `fb-present.c`; different geometry requires code changes/rebuild, not just a different device path |
| Physical touch | `/dev/input/by-path/platform-1f00080000.i2c-event`, fixed rotation/coordinate scaling | `start-rx3.sh`, `touch-bridge.c`; select your touchscreen and adapt its geometry |
| Audio output | ALSA card `DDJFLX6`, 44.1kHz, four channels with separate master/headphones | `asound.conf`, `fbshim.c`; another interface needs routing changes and playback/cue verification |
| MIDI and preferred mapping | Exactly one `DDJ-FLX6` MIDI input; the owner's BiteDJ XML and mapping semantics | `flx6-rx3.py`; `--mapping` and `--fifo` override two paths, but device discovery, jog-state path and FLX6 translation remain specific |
| Control/state paths | Host paths beneath the owner's rootfs, plus `/home/pompu_5/rx3-midi-jog-state.json` | `pi-controls.h`, `flx6-rx3.py`, `start-rx3.sh`, `stop-rx3.sh`, replay helpers |
| Executable patches | RX3 1.19 binary layout/hash and matched shim; optional tempo patch expects its stated input | `patch-player.py`, `patch-tempo25.py`, [tempo-range instructions](#preferred-bitedj-fourth-tempo-range) |

Host paths and paths **inside the chroot** are different. Guest names such as
`/dev/rx3-control`, `/dev/tsc2007_2-0048`, `/proc/udev_usb1` and
`/media/usb1/sda1` are part of the emulated RX3 environment. Do not globally
replace every `/dev`, `/proc` or `/media` string with a host path. Adapt the host
side and preserve the guest contract, or change both sides deliberately.

Useful read-only inventory commands on the target Pi:

```sh
id
lsblk -o NAME,FSTYPE,UUID,MOUNTPOINTS
ls -l /dev/dri /dev/input/by-path
cat /proc/asound/cards
aplay -l
amidi -l
```

`aplay` and `amidi` are supplied by Debian's `alsa-utils`. After adapting paths
and assembling the rootfs, `python3 prepare-runtime.py --check` inspects its
expected files/mounts without creating them. It checks only the subset encoded
in that script, not full runtime correctness. Do not treat `start-rx3.sh` as
the next step on an untouched clone.

A prebuilt shim or presenter would only skip compilation. It would retain its
compiled assumptions and would not supply firmware, a prepared rootfs, a
controller mapping or device configuration. A distributable installer/config
layer and verification on a second independently prepared Pi remain unfinished.

## Working evidence

- Analysed USB library browsing, native loading and two stacked waveforms.
- Playback confirmed audible by the owner through FLX6 cue/headphones. Master channels1/2 and headphones3/4 routed through ALSA, using stable card ID `DDJFLX6` rather than a numeric card index.
- Fullscreen landscape1920x1200 display from native1280x800; DRM page-flip presenter measures about60FPS. A sequence-checked pair of completed-frame buffers now separates composition from presentation.
- Native browser touch and A–H hot-cue touch adapters. Transport/Source controls are available before loading the first track. Browse and Source views expose compact Search, Tag List, Tag +/−, Player, Back, Source and Info buttons on the right, preserving the source/title area. Native transport strip uses its own locked RGB565 window surface; repeated presses keep labels visible in screenshot tests.
- Native Mixer panel with 17 vertical touch sliders and a horizontal crossfader and two headphone-cue buttons, sharing input state with FLX6. Touch replay verified level taps, drag, cue toggle and return to waveforms; headphone volume/cue and master mute verified in hardware output data. Startup now assigns each player to its corresponding mixer channel. Both deck faders mute their own master signal while headphone cue remains available, verified in FLX6 output data. Crossfader assignments initialize to deck1 left/deck2 right; both endpoints are verified in output data. Native FILTER is selected at startup on both channels; both decks’ low/high/center responses are verified in output data. Trim mute and all three EQ cuts passed output checks on both decks.
- 126 FLX6 MIDI bindings read from the user's installed BiteDJ XML. Jogs, tempo, tempo-range buttons, mixer, play/cue/load, browse encoder and navigation adapters.
- Touch tempo faders live in Mixer, one per deck, with native signed percentage readback, a zero detent and minus/plus buttons for native-step fine adjustment. Each deck header also exposes native tempo RANGE and KEY LOCK with engine-state feedback. Touch and FLX6 input update the same fader state. Endpoint, neutral, drag/release and playback checks passed; see VALIDATION.md.
- Native audio recovery survived actual FLX6 driver disappearance/return in one player process; MIDI reconnected and both decks played afterward. This was a driver test, not a physical cable-unplug test.
- BiteDJ files remain unchanged. Stop this runtime before returning to BiteDJ.

## Important unfinished work

The owner still sees waveform flicker and motion less smooth than BiteDJ. Presenter FPS does not establish coherent native frames or waveform cadence. Completed-frame exchange now addresses unsynchronised producer/consumer reads; perceived flicker and native waveform cadence still require verification.

Native transport is experimental. Browser/load/play/pause were exercised through touch replay; full physical touch comfort, all controls and full state feedback are not verified. Physical control comfort, MIDI LEDs, full pad/FX sound validation, shifted jogs, deck3/4 policy, sync/pickup behavior, physical unplug/card-renumber tests and a full reboot validation remain incomplete. Browser acceleration is not ported; the encoder currently moves one native step per MIDI delta. Long VIEW opens the native Tag List (Prepare equivalent); SHIFT+VIEW adds the selected track from Browse or removes it within Tag List. Scripts retain the current Pi's paths, group IDs and FLX6 card identity and require adapting to another installation.

Touch-only ZOOM−/+ buttons sit above the native ZOOM/GRID selector. They change the shared waveform scale and hide in GRID mode and Mixer. These are added touch controls using native RX3 commands.

SHIFT+jog now translates the selected MIDI deck’s beatgrid in5ms steps per16ticks, preserving scratch cancellation. Native offset and rendered grid movement passed replay tests; physical feel remains unverified. Edits outside visible GRID now use the native save lifecycle; alternating edits on both decks survived a player restart. Cross-deck interaction with an already-open GRID editor and heavy-I/O save stress remain unverified. The matched executable/shim checkpoint now uses BiteDJ’s preferred 6/10/16/25% tempo ranges, including native 25% artwork and hundredths display. This does not establish full controller parity; see the 25% range instructions below.

## FLX6 navigation

User preference: match the installed BiteDJ FLX6 behavior; disclose RX3 limitations rather than silently replacing preferred mappings. Preserve BiteDJ files.

Source of truth: installed `~/.mixxx/controllers/Pioneer-DDJ-FLX6.midi.xml` and its BiteDJ script.

| Physical control | MIDI | Behavior |
|---|---|---|
| Encoder turn | B6 40 | Open Browse from player; scroll selected browser list, never waveform zoom |
| SHIFT + encoder turn | B6 64 | Zoom the shared waveform scale from player view; ignored in Browse and GRID mode |
| Encoder press | 96 41 | Native enter/open selection |
| BACK | 96 65 | Open Browse from player; otherwise go back in browser |
| VIEW | 96 7A | Open Browse; stay there if already open |

The `[Tab]` View/Back entries were previously ignored; they are now translated with explicit intent markers. Native window136 visibility detects the player even before loading a track. Runtime physical verification remains limited.

## Build

On a Debian/Raspberry Pi OS Pi, install the native development headers and ARM32
cross compiler first:

```sh
sudo apt update
sudo apt install build-essential pkg-config libdrm-dev libfreetype-dev gcc-arm-linux-gnueabi binutils-arm-linux-gnueabi
```

`xf86drm.h: No such file or directory` (from `drm-present.h`, including when
building `test-frame-exchange`) means the native libdrm development headers
are missing or the compiler is not using their include flags. Check:

```sh
pkg-config --cflags --libs freetype2 libdrm
mkdir -p build
gcc -O2 -o build/test-frame-exchange test-frame-exchange.c $(pkg-config --cflags --libs freetype2 libdrm)
./build/test-frame-exchange
```

This test does not require firmware recovery. The full shim build below **does**
require a prepared RX3 rootfs. Pass its path as `sh build.sh /path/to/rx3-rootfs`;
the no-argument default is the original developer's `/home/pompu_5/rx3-rootfs`.
Do not use that default on a fresh machine. Recovery and rootfs assembly are
separate steps; the repository is not yet a complete fresh-system installer.

```sh
sh build.sh
python3 test-navigation.py
gcc -I . -o build/test-mixer-layout test-mixer-layout.c
./build/test-mixer-layout
gcc -O2 -o build/test-mixer-state test-mixer-state.c mixer-state.c
./build/test-mixer-state
gcc -O2 -o build/test-tempo-step test-tempo-step.c
./build/test-tempo-step
gcc -O2 -o build/test-frame-exchange test-frame-exchange.c $(pkg-config --cflags --libs freetype2 libdrm)
./build/test-frame-exchange
```

Output stays in `build/`. Build does not install or start anything. `start-rx3.sh` calls `/home/pompu_5/prepare-runtime.py` before a new player starts, so deploy that helper alongside the start script. Preparation restores device/ALSA bind mounts and the known USB export's read-only views, reusing an existing desktop USB mount when present. `python3 prepare-runtime.py --check` inspects without changes. Existing rootfs files, FIFOs and prepared writable library analysis are still prerequisites. This is not a fresh-system installer or a verified unattended boot service.

Native patch addresses are specific to RX3 v1.19. Original player SHA256: `60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09`.

## Firmware inputs

Run recovery separately from the C build, from inside this repository:

```sh
sudo apt install python3 python3-cryptography unzip libarchive-tools
git pull --ff-only
python3 recover-firmware.py
test -s aes256.key && echo "Key recovered beside recover-firmware.py"
test -s extracted/player/pdj/rbp && echo "Player file present"
```

The key is saved at `aes256.key` in the **repository root**, not under
`extracted/`. Do not print or send its contents. The script's final
`Verified original player:` message confirms the player's expected hash; the
file-presence checks alone do not verify integrity. A run that only left
`extracted/rx3.tar.bz2` did not finish player recovery. No device-specific key
or physical CDJ is needed for this source-package recovery. Inputs are pinned
to RX3 **1.19** because the current patches target that version; this is not
a claim that 1.19 is the newest firmware.

If an older recovery run ends with a bare `Killed` after key recovery or the firmware download, memory exhaustion is a likely cause (confirm with the system's OOM logs). Update the toolkit and rerun from the same directory:

```sh
git pull --ff-only
python3 recover-firmware.py
```

Keep the cached downloads. The recovery helper now hashes, joins source parts, reads the nested initramfs, decrypts sectors, and extracts files as streams instead of holding whole archives in RAM. Verified completed downloads are reused; interrupted `.partial` files are recreated. Recovery of the pinned RX3 1.19 inputs passed under a 192 MiB address-space limit with about 79 MiB peak Python RSS, producing the same known-good ISO/player. This does not change the supported firmware version.

Streaming regression tests (requires the existing `cryptography` dependency):

```sh
python3 -m unittest discover -s tests -v
```

No proprietary firmware, music, library database, SSH credentials or machine image is committed. `recover-firmware.py` downloads hash-verified official source/update packages and extracts the firmware key from the published source package. It creates local outputs only and does not flash hardware. `patch-player.py` expects `pi-runtime/rbp` and generated `pi-clock.bin`; rootfs assembly remains a documented outstanding task.

Screenshots are evidence of the development checkpoint. The Pi backlight can remain at0 while memory screenshots are taken. Do not re-enable it while the owner sleeps.

The Mixer shows FADER % and effective playback BPM separately, so retained Sync/pickup tempo is visible even when the fader is centered. After Sync is switched off, fine tempo buttons first catch a held tempo within the selected range, then apply one native step. Active Sync remains under native control. Held tempos outside the current range require widening the range; different-track pickup was checked in WIDE on both decks; extreme-BPM cases and the audible transition still need validation.

FLX6 tempo inputs now use soft pickup after a touchscreen tempo change: move the hardware fader to or across the touch setting before it takes control. This applies to the updated bridge and shim together. The Mixer shows amber MATCH FASTER / MATCH SLOWER until pickup, or MATCH FADER before a hardware position is known. These describe speed direction; physical feel remains unverified.

Pressing the FLX6 browse encoder from the player screen opens Browse. Inside Browse it enters the selected pane/item or opens the native Track Menu; rotation and another press can select Load to Deck 1/2.

Touch Tag List opens the Prepare equivalent; Tag + adds the selected track from Browse and becomes Tag − within Tag List for removal. Player returns directly to the decks from Tag List. Existing Player/Back/Source/Info touch positions are unchanged.

Touch Search opens the native on-screen keyboard. Type a query, tap a result to hide the keyboard, then use its Load1/Load2 buttons. Search occupies physical x945,y30 in the browser toolbar; all previous navigation positions remain unchanged.

### Preferred BiteDJ fourth tempo range

Build the current shim, then create a separate executable candidate with `python3 patch-tempo25.py ORIGINAL_RBP_PI OUTPUT_RBP_PI`. The input must be the unmodified-in-tempo RX3 v1.19 Pi executable; already-patched input is rejected. Stop RX3 before replacing its executable and shim together, and retain both originals for rollback. The script does not ship or download firmware. `build.sh` builds the shim but does not apply this separate executable patch.

The fourth range becomes25%, including original counter artwork and hundredths tempo display. `generate-tempo25-label.py` and `generate-mixer-labels.py` regenerate label headers using ImageMagick and Liberation Sans. The native artwork hook checks the patched engine and snapshot tables, image dimensions and format before writing. Runtime status `rx3_tempo25_artwork_state` is1 after success, negative on validation failure. Use the matching executable and shim as a pair.
