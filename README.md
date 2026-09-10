# RX3 on Raspberry Pi — development checkpoint

Experimental compatibility work running the ARM32 RX3 v1.19 player on Raspberry Pi 5 (4GB), Debian, Raspberry Pi Touch Display 2, and DDJ-FLX6. This is the embedded RX3 application, not desktop rekordbox.

## Working evidence

- Analysed USB library browsing, native loading and two stacked waveforms.
- Playback confirmed audible by the owner through FLX6 cue/headphones. Master channels1/2 and headphones3/4 routed through ALSA, using stable card ID `DDJFLX6` rather than a numeric card index.
- Fullscreen landscape1920x1200 display from native1280x800; DRM page-flip presenter measures about60FPS. A sequence-checked pair of completed-frame buffers now separates composition from presentation.
- Native browser touch and A–H hot-cue touch adapters. Transport/Source controls are available before loading the first track. Browse and Source views expose compact Player, Back, Source and Info buttons on the right, preserving the source/title area. Native transport strip uses its own locked RGB565 window surface; repeated presses keep labels visible in screenshot tests.
- Native Mixer panel with 17 vertical touch sliders and a horizontal crossfader and two headphone-cue buttons, sharing input state with FLX6. Touch replay verified level taps, drag, cue toggle and return to waveforms; headphone volume/cue and master mute verified in hardware output data. Startup now assigns each player to its corresponding mixer channel. Both deck faders mute their own master signal while headphone cue remains available, verified in FLX6 output data. Crossfader assignments initialize to deck1 left/deck2 right; both endpoints are verified in output data. Native FILTER is selected at startup on both channels; both decks’ low/high/center responses are verified in output data. Trim mute and all three EQ cuts passed output checks on both decks.
- 119 FLX6 MIDI bindings read from the user's installed BiteDJ XML. Jogs, tempo, mixer, play/cue/load, browse encoder and navigation adapters.
- Touch tempo faders live in Mixer, one per deck, with native signed percentage readback and a zero detent. Touch and FLX6 input update the same fader state. Endpoint, neutral, drag/release and playback checks passed; see VALIDATION.md.
- Native audio recovery survived actual FLX6 driver disappearance/return in one player process; MIDI reconnected and both decks played afterward. This was a driver test, not a physical cable-unplug test.
- BiteDJ files remain unchanged. Stop this runtime before returning to BiteDJ.

## Important unfinished work

The owner still sees waveform flicker and motion less smooth than BiteDJ. Presenter FPS does not establish coherent native frames or waveform cadence. Completed-frame exchange now addresses unsynchronised producer/consumer reads; perceived flicker and native waveform cadence still require verification.

Native transport is experimental. Browser/load/play/pause were exercised through touch replay; full physical touch comfort, all controls and full state feedback are not verified. Physical control comfort, MIDI LEDs, full pad/FX sound validation, shifted jogs, deck3/4 policy, touch tempo fine adjustment/range/key-lock access, physical unplug/card-renumber tests and a full reboot validation remain incomplete. Browser acceleration is not ported; the encoder currently moves one native step per MIDI delta. VIEW-long/SHIFT variants remain unmapped. Scripts retain the current Pi's paths, group IDs and FLX6 card identity and require adapting to another installation.

## FLX6 navigation

Source of truth: installed `~/.mixxx/controllers/Pioneer-DDJ-FLX6.midi.xml` and its BiteDJ script.

| Physical control | MIDI | Behavior |
|---|---|---|
| Encoder turn | B6 40 | Open Browse from player; scroll selected browser list, never waveform zoom |
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
gcc -O2 -o build/test-frame-exchange test-frame-exchange.c $(pkg-config --cflags --libs freetype2 libdrm)
./build/test-frame-exchange
```

Output stays in `build/`. Build does not install or start anything. `start-rx3.sh` calls `/home/pompu_5/prepare-runtime.py` before a new player starts, so deploy that helper alongside the start script. Preparation restores device/ALSA bind mounts and the known USB export's read-only views, reusing an existing desktop USB mount when present. `python3 prepare-runtime.py --check` inspects without changes. Existing rootfs files, FIFOs and prepared writable library analysis are still prerequisites. This is not a fresh-system installer or a verified unattended boot service.

Native patch addresses are specific to RX3 v1.19. Original player SHA256: `60bcbd8876116bf09f0d8f747f95d7c7d3081ebd39d6fe14d56005a22f7f3b09`.

## Firmware inputs

No proprietary firmware, music, library database, SSH credentials or machine image is committed. `recover-firmware.py` downloads hash-verified official source/update packages and extracts the firmware key from the published source package. It creates local outputs only and does not flash hardware. `patch-player.py` expects `pi-runtime/rbp` and generated `pi-clock.bin`; rootfs assembly remains a documented outstanding task.

Screenshots are evidence of the development checkpoint. The Pi backlight can remain at0 while memory screenshots are taken. Do not re-enable it while the owner sleeps.
