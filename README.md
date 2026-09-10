# RX3 on Raspberry Pi — development checkpoint

Experimental compatibility work running the ARM32 RX3 v1.19 player on Raspberry Pi 5 (4GB), Debian, Raspberry Pi Touch Display 2, and DDJ-FLX6. This is the embedded RX3 application, not desktop rekordbox.

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

SHIFT+jog now translates the selected MIDI deck’s beatgrid in5ms steps per16ticks, preserving scratch cancellation. Native offset and rendered grid movement passed replay tests; physical feel remains unverified. Edits outside visible GRID now use the native save lifecycle; alternating edits on both decks survived a player restart. Cross-deck interaction with an already-open GRID editor and heavy-I/O save stress remain unverified. Known mapping difference: BiteDJ’s final tempo range is25%; RX3 currently uses WIDE100%. Neither behavior is claimed as full parity.

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

On the Pi, with ARM32 cross compiler and native gcc, FreeType/libdrm development packages:

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
