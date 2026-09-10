# Checkpoint validation

Built the committed shim, presenter, touch bridge and ARM clock stub on the Pi with `sh build.sh`. Navigation parser test passes locally and on the Pi: fragmented messages, MIDI realtime interleave, NoteOff, View/Back release suppression, encoder direction and enter press/release.

Live MIDI reader loads87bindings. Replayed VIEW(96 7A) from the initially unloaded player opened the native Browse/source page, proving the new main-panel visibility path works before waveform allocation. Existing native browser load and touchscreen coordinates remain functional in fullscreen.

Native transport surface repaint preserves text after repeated play/pause presses; earlier FillRect-based repaint lost labels and was replaced. Current native touch is the four-source shim including `native-ui.c`. Screenshot `native-transport.png` demonstrates the transport layout. Cue/Sync/Info and prolonged browser transitions need continued verification; no claim that all touchscreen controls are complete.

Physical user has confirmed audio and stacked waveforms but still reports flicker and less smooth motion than BiteDJ. The~60FPS measurement describes presentation only. Backlight0 verified; screenshots continue while screen is off.

This is a development checkpoint, not completion of the larger project.

## Completed-frame presentation

Added a hook after `DS_HW_UpdateScreen` layer0 returns. It copies into one of two shared4MB buffers and release-publishes a sequence number. The presenter copies the selected buffer and accepts it only if the sequence remains unchanged; on a collision it retries or holds its last complete frame. Rendering never depends on the backlight.

`test-frame-exchange.c` includes the actual presenter reader and races it against a separate process writing500uniform generations. On Pi it checked27accepted frames with no mixed generation and verified final generation500. The deliberately unthrottled producer caused retries, as expected. This validates exchange consistency, not native compositor correctness or perceived motion.

Live fullscreen presentation measured60FPS and about10.5ms draw time, with180accepted snapshots per180displaycycles in sampled intervals. Native screenshot captured from sequence6408 shows two loaded waveforms and the transport strip. The user still needs to assess flicker visually with the backlight on later; this is not a claim of fully smooth waveform motion.

Fixed stop-rx3.sh to match fullscreen/coherent helper arguments. Prior fullscreen helpers were not stopped by the old exact-argument matcher. Subsequent controlled restart replaced both helpers successfully; screen remainsdark.

## Touchscreen startup flow

Shared `native-screen.h` detects the main deck panel before waveform allocation. The native strip now appears on an empty player and offers Source in its last slot. Regenerate its checked-in glyphs with `python3 generate-native-labels.py` (ImageMagick and Liberation Sans required).

From freshly restarted player with no tracks loaded, replayed only touchscreen coordinates through the physical input bridge: Source(1800,30), USB2row(600,350), rowarrow(1040,350), Tracktab(75,345), Load1(1620,187), Play1(360,30), Cue1(600,30). USB2 displayed13646songs; Aaliyah/Try Again loaded, playback advanced to04:33.773remaining, and Cue returned to04:43.942. No direct load/play/control FIFO commands were used for this flow. These are software replay checks, not physical finger testing.

The small native transport surface is fully repainted under one lock on each GUI pass. After Cue,118completed-frame samples all retained2435white text pixels; complete-frame sequence10244 screenshot confirms labels and paused cue position. Some raw framebuffer screenshots caught missing labels during redraw; they are not evidence of displayed label loss. Use completed-frame capture for future visual checks. Backlight stayed0; presentation remained60FPS.

## Stable FLX6 audio identity

Replaced numeric `hw:2,0` in the dmix slave with `hw:CARD=DDJFLX6,DEV=0`, and the control-device redirect with `hw:CARD=DDJFLX6`. The ALSA card-name lookup resolved to the connected FLX6 and its control device opened successfully. After rebuilding/restarting, hardware negotiation remained four-channel S16_LE at44100Hz, period128frames, buffer512frames.

Touch replay loaded and played Aaliyah/Try Again. Completed-frame screenshot showed the native playback position advancing. The hardware stream was RUNNING with advancing hardware pointer; direct inspection of its mapped DMA buffer found changing, nonzero samples on all four channels across three captures (RMS approximately104–346 in signed16-bit units). This establishes active output data, not a new human listening test. Physical USB enumeration changes and unplug/replug recovery were not exercised. Backlight remained0.

## Shared mixer input state (view not yet implemented)

Added a state observer to the common native-key dispatcher used by initialization, FIFO/FLX6 commands and touchscreen pad/button commands. It records all16mixing controls plus debounced headphone-cue presses. Values mean last dispatched input, not DSP acknowledgement. The future native mixer view must retain this distinction and verify actual engine effects separately.

Host and Pi tests passed for all16bindings, channel isolation, invalid/nonfinite value rejection in metadata, and cue press/release handling. Live process inspection verified startup validmask65535, all expected level defaults and headphonecue1. Replayed actual FLX6 channel1 fader messages B0 13/B0 33 and headphone-cue90 54: state changed to4096/16383 and cueoff, then restored to fader1/cue1. Native dispatch continues unchanged. No mixer view/button has been added by this commit.

## Native touchscreen mixer checkpoint

Added a native RGB565 Mixer window below the transport strip: 16 sliders for both decks and output/headphone controls, plus headphone cue per deck. The ninth strip button opens/closes Mixer. State reflects last dispatched input, not DSP acknowledgement. Blank panel gestures are consumed through release; active slider gestures cancel when leaving the main panel. Failed surface validation disables and hides the panel on the next draw.

Pi build and controlled deployment succeeded. Completed-frame captures verified initial layout, deck1 level tap to50%, headphone cue1 toggle off, continuous level drag from100% to50%, and close returning to loaded Aaliyah/Try Again waveform at its cue position. Restored deck1 level100%; headphone cue1 enabled. Browse hides Mixer correctly, but entering Browse with no source selected leaves no visible touch route back. A direct native Source command recovered that test, followed by touch-only USB2 selection and track loading. This gap remains open.

No physical finger, multitouch, MIDI-to-panel repaint or individual DSP-effect verification is claimed by this checkpoint. Backlight stayed0.

## Browse navigation by touch

Native strip remains visible across active screen0's player, Browse and Source views. Player mode retains transport/mixer controls; other views show Player (native Browse toggle), Back and Source. Non-strip native list touches still pass through, and the mixer/pad adapters stay restricted to the main panel.

From a fresh player without a source, touch Browse opened the empty list; touch Player returned to the empty player. Re-entered Browse and touched Source to open device selection. Selected USB2, entered Track, and exercised Back, which dismissed selected-track load controls. Selecting the first track again and tapping Load1 loaded Aaliyah/Try Again. Subsequent Play/Cue replay returned to its cue point. All navigation in this verification used the touch bridge, without direct FIFO navigation commands. Pi build and navigation regression test passed. Backlight remained0.

The strip occupies the native header's upper44pixels, including its original title/Info area. Header information/Info access needs a layout refinement. Some transition captures lacked the Source label; a later cued capture contained all nine labels. This remains a rendering observation to investigate, not proof of a fully flicker-free UI.

## Mixer output verification and deck-fader failure

Live player PID15801, FLX6 four-channel S16LE hardware buffer,40 reads of512frames at25ms intervals per measurement. Reads were from the existing mapped playback DMA buffer; this verifies generated output data, not a fresh human listening test. Touch replay controlled the panel.

| Control state | Master L/R RMS | Headphone L/R RMS | Result |
|---|---|---|---|
| Initial playback |184.39 /173.74|259.12 /244.16|Both output pairs active|
| Headphone volume0 |127.17 /127.87|0 /0|Headphone pair silent, master active|
| Headphone volume restored~50% |188.10 /172.04|264.23 /241.68|Headphone pair active again|
| Master0 |0 /0|447.23 /460.14|Master pair silent, headphone cue active|
| Master restored~60%, deck1 level0 |164.24 /165.73|457.15 /460.98|FAIL: master should be silent for the only playing deck|
| Deck1 level restored100%, cue1 off |234.84 /243.62|0 /0|Cue button silences headphone pair|
| Cue1 on |207.61 /219.84|288.52 /305.50|Cue audio restored|

Different rows sample different portions of the song; nonzero RMS ratios are not transfer-function measurements. Silent pairs had both zero RMS and zero peaks. All playing measurements had40distinct buffers.

Replayed FLX6 B0 13 20 / B0 33 00 through the real MIDI bridge. Mixer screenshot displayed deck1 level25%, proving MIDI-to-panel feedback through shared state. This does not prove physical knob/fader handling.

Repeated deck1 level0 test still left master audio. Read-only process inspection confirmed mixer input0 fader value0.0, curve1, target gain0, settled residual~7.7e-32. Native curve tables end in0, so blindly translating the fader to a different input range would be unjustified. Native path is onEv_VolumeFader0x2d35a0 -> DjEngineIF0x4c68c -> MixerEngine0x56ed4 -> ChannelFader::setFader0x9bb54. Cueing deck1 then made all four hardware channels exactly zero. Investigate downstream mixing/output routing or a parallel deck signal path. Deck1 fader restored100%; player paused at cue; backlight0.

## Fixed duplicate deck-to-mixer routing

Root cause of the prior fader failure: MixerRouteMngr assigned both mixer inputs0and1 to player0. Read-only route table inspection at0x1149f08+72 showed both pointers0x1149f08; both mixer input buffers carried deck1. This left deck1 audible through fader2 when fader1 was lowered.

Control initialization now invokes the native DjEngineIF::setRoute API0x50598 for player0->input0 and player1->input1 before playback. The temporary experiment clearing virtual capture buffers did not resolve the issue and was removed; fbshim.c is unchanged. No arbitrary fader scaling or output muting workaround was added.

After a fresh build/restart, touch-loaded deck1 and played it. Master RMS91.94/91.30, headphone cue258.44/256.62. Fader1 at0 produced exactly zero master RMS/peaks while headphone cue remained179.34/186.48. Restoring fader1 produced master94.53/85.72. Loaded a different track (Able to Maximize) on deck2 and cued deck1. Deck2 master312.45/309.16; fader1 at0 left deck2 master372.42/375.62; fader2 at0 gave exactly zero on all outputs with cue2 off; restoring fader2 restored319.69/320.72. These are separate song positions, not gain-ratio measurements.

The deck2 load required a later Play tap after loading finished; rapid scripted input immediately following Load was not accepted. Touch readiness around load transitions remains to improve. Native source/mixer reassignment modes beyond this startup mapping are not yet verified. Navigation and mixer-state regression tests passed. Both deck levels restored100%, both players cued, cue1 enabled/cue2 disabled, backlight0.

## Crossfader assignment and endpoint verification

Crossfader initially had no audible effect: read-only native mixer inspection showed assignment0 (bypass) on both input channels. Startup now invokes DjEngineIF::setCrossFaderAssign0x4cc0c with input0/assignment1 (left/A) and input1/assignment2 (right/B). No fader-value scaling changed.

Fresh runtime PID17134: deck1 playing, cross value1 gave master RMS/peaks exactly0 while cue remained234.71/230.90 RMS; value0 restored master107.40/97.04. Deck1 then cued and Abacus loaded on deck2. With cue2 enabled, value1 gave master50.67/34.64 and headphones142.35/97.36; value0 gave exactly zero master and headphones144.57/127.08; returning to1 restored master47.68/40.66. Each playing sample contained40distinct hardware buffers. Thus both opposite-deck endpoint mutes and prefader headphone monitoring are verified in hardware output data.

Important replay correction: Load buttons follow the currently selected track row. One attempted deck2 load used stale first-row coordinates and never loaded a track; screenshots showed the selected Abacus row's Load2 at physical1812,562. Clicking that observed position loaded successfully. Zero output before confirmed load/play was excluded from the endpoint evidence. Earlier claims attributing all such misses to load timing were too strong; use current screen evidence before replaying dependent steps.

Crossfader returned to center; both decks cued; deck levels100%, cue1on/cue2off; backlight0. The panel still represents crossfader as a vertical slider: a horizontal A/B layout is an open usability improvement.

## Native filter enabled and deck1 response verified

Native SoundColorFxManager type was0 (off) for both inputs, making the Filter sliders ineffective. Replaying native CfxFilter key0x50a6 changed both types to1, confirming the native Filter selection. Startup now sets type1 explicitly through DjEngineIF::setSoundColorFxType0x4e2c4 for input0and1. An explicit selection avoids accidentally toggling an already-enabled effect off. The existing normalized ColorKnob path is unchanged.

Fresh runtime PID17598 reported type1 on both channels. Touch-loaded deck1 Aaliyah/Try Again, then returned to cue before each playback sample: center, lower end, upper end, center. Each measurement reads40hardware DMA snapshots of512four-channel frames, spaced25ms, and reports mean square first sample differences divided by sample energy (a high-frequency-content indicator, not a calibrated frequency response). Master L/R ratios: center0.03743/0.03492; low0.00465/0.00641; high0.83327/0.79357; center again0.03402/0.03560. Headphone cue showed corresponding changes. All samples contained40distinct buffers.

This demonstrates spectral change in the expected directions and return near baseline, rather than merely slider feedback or changing RMS. Samples are not phase-aligned or calibrated sweeps. Independent deck2 spectral response and physical FLX6 filter gestures remain to verify. Regression navigation/mixer-state tests passed. Deck1 paused at cue, filtercenter, mixerclosed, backlight0; deck2 unloaded after restart.

## Deck1 trim and EQ output measurements

Existing runtime PID17598; no runtime code change required. Touch trim0 produced exact zero RMS and peaks on all four FLX6 channels, compared with initial master59.46/54.04 and headphones237.12/215.52 RMS. Trim restored to center.

For each EQ measurement, returned deck1 Aaliyah/Try Again to cue, changed only the indicated EQ control, and played again. An independent diagnostic used40mapped-DMA snapshots,512frames each,25ms apart, a Hann window and radix2 FFT. Frequency bins grouped below300Hz,300–4000Hz,and above4000Hz. The FFT/grouping self-check passed with pure tones in each band. Powers below are arbitrary consistent units, not calibrated dB or speaker measurements.

| Setting | Low power | Mid power | High power |
|---|---:|---:|---:|
| All centered |43001446.8|121806246.4|1911468.0|
| High minimum |44654278.2|87752479.6|532545.9|
| Mid minimum |27171183.0|4183373.1|450866.7|
| Low minimum |5058780.5|114337369.8|1675513.9|

All three touch controls affect actual output in their expected frequency regions. Samples begin near the same cue but are not phase-aligned; these measurements do not establish exact crossover frequencies or manufacturer EQ curves. Each contained40distinct buffers. Restored trim and all EQ controls to center, player cued, mixerclosed, backlight0. Independent deck2 EQ isolation, boosts, and physical knob operation remain unverified.

## Horizontal touchscreen crossfader

Moved crossfader to a full-width horizontal track, labeled Deck1 left and Deck2 right. Master, headphone volume and headphone mix now share the center bank as three wider columns. Native key mapping and normalized crossfader values remain unchanged. Shared native-mixer-layout.h defines the renderer column centers, touch regions and value conversion; the label generator uses the corresponding column widths.

Pi build/deployment succeeded. Completed-frame images verified centered layout, a continuous physical-input replay drag fromx90through1840 at y978 reaching the right endpoint, left tap, center tap, and independent headphone-volume0 at its new location. Restored headphone volume50%. Layout checks passed locally and onPi for every vertical slider center, horizontal endpoints/center/clamping, and blank gaps. Native navigation and mixer-state regressions passed. These checks establish touch dispatch/rendering, not a new audio endpoint test; native crossfader DSP endpoint tests are recorded above.

Updated physical replay coordinates: crossfader y978, left margin90, center960, right margin1840. Master columncenter~800; headphone volume960; headphone mix1120. Vertical endpoints remain y285/920, midpoint599. Deck-control and headphone-cue button positions remain unchanged. Screen staysdark; player has no tracks loaded after this restart.

## Compact browser navigation and native Info

Split the native strip into mutually visible surfaces: full player transport atx0,width1280, and navigation atx880,width400. Browser navigation has Player/Back/Source/Info at100nativepixels each. The left880pixels now retain the native source/title area. The navigation block still occupies the original right-hand timer area; this is not a complete preservation of every header indicator.

Distinct native window keys are required as well as determining stacking. Player uses1, mixer2, navigation3. An initial build reused1, causing CreateWindow to return4 and disable the strips; that build was corrected before this checkpoint. Failure stage/result diagnostics remain available in rx3_ui_failure. Format9 surfaces are rendered as RGB565 with their returned row pitch, including padding.

After rebuilding/restarting, touch Browse from an empty player displayed 'Please select a source' beside the compact buttons. Player returned to the main screen. Source->USB2->Track preserved 'USB2 TRACK'; Info key0x20b opened the native metadata pane (duration04:44,BPM93.0,keyE,artwork/rating/date). The observed Info-pane Load1 button at physical1365,938 loaded Aaliyah/Try Again; a later completed frame showed its waveform and cue time04:43.942 with full player transport restored.

Physical top-row button centers in Browse/Source: Player1395, Back1545, Source1695, Info1845 (all y30). Main player coordinates are unchanged. Transition frames can still temporarily omit overlay labels; later stable frames show all buttons. Navigation/mixer-state/layout regressions passed. Backlight0; deck1 loaded/cued and deck2 unloaded.

## Retained transport/navigation strip rendering

The native strip now repaints only on visibility or pressed-button changes, reusing its retained RGB565 surface on other GUI passes. This removes repeated pixel fills and glyph painting without changing native compositor or frame-publication hooks. Visibility changes invalidate the cache so switching between player/navigation repaints correctly.

Before the change:188stationary player frames all had2748bright label pixels. A timed Browse transition changed the right-hand region from1020player-label pixels to1251navigation-label pixels without an empty interval; Info toggle kept1251through172sampled frames. The previously observed transition omissions were not reproduced in these samples, so this is an efficiency improvement, not a demonstrated flicker fix.

After a fresh build/restart:125empty-player frames retained2748pixels. Browse transition again moved directly between expected counts. Touch-selected USB2/Track and loaded the observed first-row Load1. During playback198distinct completed frames all retained2748label pixels; after Cue196frames also retained2748. Hardware audio contained40distinct buffers with nonzero master/headphone data during playback. Navigation, mixer-state and layout regression tests passed.

The probe reads only the top44rows from sequence-verified frame snapshots and counts pixels whose RGB components are all>=220. It establishes sampled label retention, not waveform frame rate, visual smoothness, or absence of all possible transition artifacts. Backlight remains0; deck1 cued, deck2 unloaded.

## Runtime mount recovery

Added prepare-runtime.py and invoked it from start-rx3.sh before launching a new player. It restores bind mounts for dev/null,zero,urandom,full,snd and proc/asound; restores USB1 by known filesystem UUID; mounts USB2 Contents/Music/Artwork read-only. It leaves the local export database/analysis untouched, rejects unexpected mount sources, and provides --check with no mutations. It preserves the firmware's fake proc files rather than mounting over the entire proc directory.

When the desktop already mounts this FAT filesystem read/write, a second direct read-only filesystem mount fails with conflicting RO state. Preparation now locates the existing whole-filesystem mount and creates a read-only bind view instead. The desktop mount retained its original rw/UTF8 options after recovery. A direct read-only mount is only attempted when no existing external whole-filesystem mount is found; that branch and the absent-USB path remain untested live.

With RX3 stopped, removed all ten runtime bind/library mounts. --check failed as expected. Preparation restored all ten and a subsequent --check passed. SHA256 of local export.pdb and a sampled USBANLZ EXT file stayed unchanged across preparation. New startup ran the preparation step and launched the player. Touch-browsed USB2, inspected the current selected row, loaded Aaliyah/Try Again, and played: hardware DMA showed nonzero master/headphone output with40distinct buffers. Player then cued. Backlight stayed0.

This tests loss/recreation of runtime mounts on the existing Pi, not a complete reboot. Firmware/rootfs assembly, persistent device-file provisioning, desktop/display startup ordering, and unattended boot service still require work. BiteDJ files were not modified.

## Deck2 mixer output checks

Live PID19723 after mount recovery. Inspected the selected first-row Load2 button and loaded Aaliyah/Try Again on deck2. Used the same40-snapshot Hann/FFT diagnostic as deck1, returning to cue between settings. All playback rows had40distinct buffers except trim mute, which was exactly silent.

| Deck2 setting | Master left RMS | Low power | Mid power | High power |
|---|---:|---:|---:|---:|
| Centered baseline |57.325|50990832.0|100088482.5|1686284.3|
| Trim minimum |0|0|0|0|
| High minimum |47.246|47420747.6|63429651.6|581139.7|
| Mid minimum |21.576|16178384.1|4307457.8|450209.8|
| Low minimum |47.660|5822503.8|125432013.8|1973820.1|
| Filter low |55.007|123438764.3|5777751.5|414845.6|
| Filter high |5.900|4082.7|339768.0|1335624.9|
| Restored center |57.992|55204308.2|142187776.1|1778326.5|

These establish expected band effects on deck2, not calibrated EQ curves. Separately, deck1 RMS58.423 baseline remained57.292 with deck2 trim/EQ minima and its filter high; thus the deck2 mute did not mute deck1. Unaligned music snapshots cannot prove absolutely zero EQ crosstalk or identical sample output. Physical knobs and gain boosts were not exercised.

Both decks cued with trim/EQ/filter centered, levels100%, crosscenter, cue1on/cue2off, mixerclosed and backlight0. No runtime code change was needed.

## FLX6 MIDI reconnection

The input reader now waits for an absent FLX6 and rediscovers its ALSA address after a read failure. Disconnect cleanup releases held buttons and jog motion, clears running status/partial messages/14-bit MSBs, and preserves absolute jog counters. Retry delays avoid spinning on a still-listed failed device; SIGTERM can interrupt the wait.

`python3 test-midi-reconnect.py` passed locally and on the Pi. It runs the real bridge/parser with a simulated ALSA transport: absent device, held jog plus pending motion, ENODEV, release events, partial-message reset, stale MSB rejection, changed hw:2 to hw:3 address, and shutdown while absent. `python3 test-navigation.py` also passed. The deployed reader loaded all 87 BiteDJ bindings and opened the real FLX6 hw:2,0,0. Only the MIDI reader restarted; native player PID19723 continued, backlight remained 0.

Physical unplug/replug and USB audio recovery remain unverified. This change does not restart or recover the native player's ALSA audio handles after USB removal. LED feedback, pad-mode switching, physical jog feel and waveform flicker remain open.

## Waveform cadence baseline

Read-only completed-frame probe sampled native waveform rectangles x420..1079, y80..235 and y302..457. It copied the full framebuffer between acquire sequence checks, then hashed RGB pixels and counted bright waveform pixels. Three runs used Aaliyah/Try Again at the existing zoom. The physical backlight stayed off; this measures published pixels, not visible LCD flicker.

| State | Accepted frames | Publication Hz | Deck1 changes/s | Deck2 changes/s | Longest observed change gap |
|---|---:|---:|---:|---:|---:|
| Both paused, 3 seconds |174|57.84|0|0|N/A|
| Deck1 playing, 8 seconds |459|57.51|37.34|0|66.94 ms|
| Both playing, 8 seconds |461|57.62|37.45|37.58|43.52 ms|

Paused waveform hashes and bright counts were identical across all samples, including paused deck2 while deck1 played. No sampled playing waveform region emptied. One sequence was missed in the deck1-only run; none in the other runs. The median moving-region change interval was about 26.3–26.7 ms. Presenter logs separately reported 60 FPS. These results establish irregular waveform pixel updates below publication cadence; they do not prove a fixed FPS cap, identify the engine timer responsible, rule out partial-region flicker, or demonstrate a fix. Both decks returned to cue through touchscreen replay after measurement. Player PID19723 stayed running.

## Waveform timing path narrowed

Read-only disassembly and live memory sampling distinguish position updates from waveform pixel changes. `ui_ComputeDispTime` (0x18cfd8) calls `UiUpdatePlayer` and `UiGetPlayTime`; its two 16-byte output records begin at 0x0551ab08. An eight-second deck1 playback sample observed 461 position changes over 7.984 seconds (about 57.7/s), with median 17.40 ms and maximum 25.89 ms between observations. Deck2 stayed at its cue position. This is substantially faster than the previously measured ~37.4 waveform-region changes/s. The likely investigation target is now waveform drawing/position-to-pixel conversion, rather than stalled playback-position updates. The probe cannot identify which draw-stage condition is responsible.

The GUI loop passes elapsed time to `ui_com_draw` each iteration. The live NS GUI timer list at 0x024935f8+84 was empty in this main-player state. `Ui_CycleTask` contains a 15 ms `dly_tsk` call, implemented as nanosleep, but no evidence establishes that delay as the waveform bottleneck. `UiHid_NotifyDetailedWaveformUpdate` is gated on PC-control mode, and the waveform watcher waits on events; these are not demonstrated frame-rate caps. No timing patch was applied. Deck1 returned to cue using touch replay; screen remained dark.

## Waveform repeat rate explained by native pixel scrolling

A native encoder event changed zoom index2 to3 for an eight-second trial, then restored index2 in a `finally` block. At index3 the deck1 waveform ROI changed on every published frame: 57.63 changes/s, median17.35ms and maximum26.31ms. Deck2 remained cued and pixel-identical. The native encoder event used key0x420c/op4 with no browser-intent tag; the normal FLX6 mapping remains Browse.

Disassembly of `ui_Playmode_Wave_ST_Init.part.0` (0x24dbb0) supplies the explanation. It multiplies computed playback milliseconds by0.15, divides by the float scroll factor, and converts to an unsigned integer at0x24dc94 before storing the waveform position at0x02498c88+12 (deck2 stride32). The factor at+24 was read live as4.0 on both decks after restoring zoom2. Thus normal-speed scrolling advances at **1000 ×0.15 /4 =37.5 whole native pixels/s**. This matches the measured ~37.4 waveform changes/s even though position updates and frame publication run at~58Hz. At this zoom, counting distinct waveform pixel regions is therefore not a measurement of renderer FPS or proof of a rendering bottleneck. Earlier wording that suggested a slowdown after position calculation should be read with this correction.

This explains repeated waveform images at the tested zoom; it does not establish that all user-visible flicker is expected or resolved. The presenter also scales1280x800 to1920x1200 using nearest-neighbor sampling; an alternating1/2 output-pixel step from native whole-pixel motion is a possible additional source of uneven-looking motion, not yet verified visually. No timing, scaling, or waveform-rendering patch was applied. Both decks returned to cue, zoom2 restored, backlight0.

## Touch input recovery

`touch-bridge.c` now waits for the stable input path, reopens it after loss, refreshes axis ranges, and handles SIGTERM/SIGINT with gesture cleanup. Active native contact is released with the existing ten-report cadence before exit/retry. SYN_DROPPED also releases gestures, clears finger ownership, and ignores events through the next SYN_REPORT. Contacts already held during recovery must be lifted and touched again; stale coordinates are not used to recreate a press.

`python3 test-touch-recovery.py` passed locally and on Pi. It compiles and runs the actual bridge against isolated paths, sends Linux evdev replay packets, and verifies native up reports after EOF, SIGTERM and SYN_DROPPED. It also checks that motion without a fresh tracking ID cannot resume the dropped press, fresh contact works, and an absent-device wait stops cleanly. These tests do not simulate real evdev disconnect/reopen; physical reconnection remains unverified.

Deployed only the rebuilt touch bridge; native player PID19723 continued. Real panel path opened successfully. Touch replay through the deployed binary started deck1: forty distinct DMA buffers, master RMS60.34/56.45 and headphone RMS240.39/224.93. Cue replay then restored deck1 to cue. Backlight remained0. BiteDJ files unchanged. Backup: `/home/pompu_5/rx3-touch-bridge-pre-recovery`.

## Real evdev reconnect test with isolated uinput device

`sudo python3 test-touch-evdev-reconnect.py` passed on the Pi. It creates temporary Linux uinput devices and runs the actual bridge against a temporary symlink and isolated report/control/state files. The new optional `--exclusive` flag acquires EVIOCGRAB before test contact injection, preventing other input consumers from receiving those contacts. The physical-panel startup command remains unchanged.

The test starts with an absent path, connects a virtual device, holds a touch, destroys the device, verifies ten native release reports, then reconnects through the same path with axis maxima changed from1199/1919 to599/959. Fresh contact maps to the same native coordinates2025/1995, proving the bridge refreshes axis ranges when reopening. The process survives device loss and exits cleanly on SIGTERM, releasing the second contact. Temporary virtual devices were destroyed during cleanup. The existing replay recovery tests still pass.

This verifies the real Linux evdev loss/reopen path, including ioctl range discovery. It does not verify physical I2C panel-driver or cable recovery, or resume contacts held across a disconnect. The rebuilt bridge is deployed and connected to the real panel; native player PID19723 continued and backlight stayed0. No player control commands or music playback were sent by this isolated test.

## Native pad bank and beat-jump evidence

`PAD-MAPPING.md` records the installed BiteDJ MIDI layout, all eight live native bank values, and the selector toggle behavior. Native bank3 pad pairs were tested on deck1: ±1/2/4/8 beats produced ±645/1290/2580/5160ms at93BPM, with backward jumps returning to each paired trial's starting position. No cue slots were written or deleted. Native Hot Cue bank0 was selected at the end, and Cue was issued. The absolute cue position was not asserted unchanged across separate trials (first baseline427ms, later577ms). FLX6 beat-jump integration remains to be implemented; these are native command tests, not a claim that controller pad modes work.

## FLX6 hot-cue bank selection and default Beat Jump integration

The MIDI bridge now loads103 bindings (previously87). Hot-cue press/release packets carry native bank0 intent; the sixteen deck1/deck2 default Beat Jump mappings carry bank3 intent. The control adapter checks actual `UiGetPadMode`, dispatches the needed selector, and waits for the expected state transition before sending a press. It handles primary/secondary banks without blindly toggling on every pad. Missing acknowledgment suppresses the press after a bounded wait and logs the failure. Release packets do not select banks.

`test-pad-bank.c` passed all64 source/target bank transitions with delayed acknowledgment and a timeout case. `test-pad-mapping.py` passed eight hot cues and eight beat-jump notes on both decks, including MIDI NoteOff conversion. Existing navigation and MIDI recovery tests passed. Full Pi build passed; shim and reader deployed with backups `fbshim-pre-pad-bank.so` and `flx6-rx3-pre-pad-bank.py`.

Live parser-to-native tests started each deck in bank7, then replayed default beat-jump pads. Both decks switched to bank3 and measured+645/+1290/+2580/+5160ms, with each backward pad returning exactly to427ms. Repeated presses retained the first bank. Hot-cue bank0 was restored with native selectors; no hot-cue slot write/recall was exercised in this test. Thus hot-cue routing is unit-tested but not yet live slot-tested. Shifted jump sizes, beat loops, other pad modes and LED feedback remain pending.

After restart, both tracks loaded via touch from USB2. Touch Play1 produced40 distinct DMA buffers with master RMS58.20/53.38 and headphone231.95/212.71, then Cue1 stopped playback. Final screenshot shows both stacked waveforms and Hot Cue banks; player PID21099, backlight0. Physical controller pad interaction and simultaneous held pads across bank changes remain unverified. BiteDJ originals unchanged.

## FLX6 Beat Loop integration

Added the installed `beatloop_0.25_toggle` through `beatloop_32_toggle` mappings for both decks, using native bank1 intent0x5041. The reader now loads119 bindings. No shim rebuild was needed: the existing native bank selector handles bank1. Pad mapping tests now cover48 mapped pads with press/NoteOff behavior. Mapping, navigation and MIDI reconnect tests passed; reader deployed/restarted with backup `flx6-rx3-pre-beat-loop.py`.

Live replay began each deck in second Beat Loop bank5. All eight pads selected bank1, set the expected native numerator/denominator (1/4,1/2,1/1,2/1,4/1,8/1,16/1,32/1), enabled the loop, and disabled it on a second press. Separately, deck1 four-beat loop playback wrapped twice over six seconds; wrap observations were2.583seconds apart, with position drops2567/2565ms (sampling omits a few milliseconds around the actual2580ms boundary). Forty distinct DMA buffers showed master RMS62.22/59.48 and headphone248.06/237.12.

Final readback: both banks0, loops off, positions unchanged over300ms (deck1 4447ms, deck2 577ms). This verifies stopped playback; tests did not preserve the original temporary cue position. Native PID21099 continued throughout, screen brightness0. Physical pads, shifted jump banks, other pad modes, LED feedback and simultaneous held pads remain open.

## Held pads across bank changes

`test-held-pads.py` passes locally and on Pi. It holds two hot cues on deck1 and one on deck2, switches deck1 to Beat Loop, verifies old-pad releases precede the new press, then sends late old-bank NoteOff messages and a duplicate loop press. Neither disturbs the new held loop; deck2 stays held independently. Correct current-bank release and disconnect cleanup are also verified. Existing pad mapping, navigation and MIDI recovery tests passed.

Reader deployed with backup `flx6-rx3-pre-held-pads.py`; native PID21099 continued. Live Beat Jump parser-to-player regression again passed all±1/2/4/8 distances on both decks, returning to4447ms/577ms respectively. Hot Cue banks restored. These live checks verify normal pad routing remains functional; the overlapping physical-pad scenario is still unverified, as are concurrent native-touch/controller changes. No mode-button input mappings were invented from BiteDJ LED-output constants.

## Native touchscreen pad-mode selectors

Added `native-pad-modes.c/.h` and generated `native-pad-mode-glyphs.h`, included in the normal build. One native RGB565 window (unique stacking key4) occupies y492..517, replacing the pad-bank header with four selectors per deck. Cached rendering updates only on visibility or native mode changes. Blue marks the selected family; second-bank state adds `2`. Nonzero dark pixels prevent the previous native header text showing through the gaps. Touch dispatches the existing native selector keys0x4113–0x4116, so repeated selection retains the firmware's bank-toggle semantics. Mixer/Browse hide the row.

Full Pi build and deployment passed; backup `fbshim-pre-touch-pad-modes.so`. Touch replay selected primary/secondary modes0/4,1/5,2/6,3/7 on both decks, with the other deck unchanged. Screenshot `native-pad-modes.png` verifies labels, highlights and both second-bank indicators. Native hardware-window options confirmed key4 invisible when Mixer opened. Touch-only deck1 bank3 pad2/pad1 moved427→1072→427ms. Touch bank1 pad5 enabled a4/1 loop and a repeated press disabled it. Selector taps did not fall through to pad actions.

Both tracks reloaded through touch after restart. Touch Play1 produced40 distinct DMA buffers, master RMS60.53/54.77 and headphone241.23/218.35, then Cue1 stopped playback. Both banks0 and loops off at the end (a remembered loop region remains visible on deck1). Native PID21886, backlight0. Presenter samples after testing varied57.5–59.4FPS; this is not a waveform-smoothness fix or a calibrated performance comparison. Physical finger tests, secondary-bank actions and concurrent touch/MIDI holds remain open.

## Touchscreen Slip Loop hold and release

Native touch bank2 pad5 (one beat) was tested on both playing decks through the deployed Linux-input bridge. Each reported loop boundaries1867–2512ms (645ms at93BPM). During the hold, audible-position values wrapped within the loop while the native background/slip time continued advancing. Normal touch release and SIGTERM of the replay reader both cleared the pad-held state, exited slipping, and returned the displayed position to within7ms of the background position in the final samples.

| Deck | Release method | Additional wait for slip exit after reader finished | Final position/background (ms) |
|---|---|---:|---:|
|1|Normal release|105ms|4566/4566|
|1|Reader SIGTERM|0ms|4577/4584|
|2|Normal release|118ms|4557/4563|
|2|Reader SIGTERM|164ms|4562/4562|

These wait values are not total finger-release latency. An initial test failed by checking continuation100ms after the reader finished: deck2's pad-held flag had cleared, but slipping was still active. Follow-up traces showed the native background time continuing; waiting for the actual slipping flag to clear resolved the discrepancy. This is consistent with native quantized exit, not evidence that a cleanup patch was needed. No runtime code change was made.

Final readback over300ms confirmed both banks0, slip-loop/slipping flags0 and stationary positions577/427ms. Native PID21886 stayed running, backlight0. This verifies one-beat Slip Loop and reader cleanup on both decks; other Slip Loop sizes/banks and physical finger release still need verification.

## All first-bank Slip Loop sizes

`touch-slip-sizes-trial.py` in local research and Pi home extended the prior live test to all eight native mode2 pads on both decks. Each trial selected the bank by touch, started playback, held the pad through the deployed evdev bridge, checked loop bounds against the pad's beat fraction, released, and waited for native slipping to end. All16 trials passed. Sizes1/16,1/8,1/4,1/2,1,2,1/3,3/4 produced41,81,162,323,645,1290,215,484ms bounds at93BPM. Final playback/background difference was at most10ms. Raw results are retained in local research `touch-slip-sizes-results.json`.

Framebuffer inspection also established that native mode6 displays Release FX (brake/backspin short/long, echo out, mute, build up, ducking), rather than more loop sizes. No effect actions were triggered in that bank. No runtime patch was needed. Both decks ended in Hot Cue mode0 with slip flags clear and positions stationary over300ms at577/427ms; player PID21886, backlight0. Actual physical finger input, Release FX behavior and other outstanding compatibility work remain unverified.

## Release FX Mute audio and cleanup

Live mode6 pad4 touch tests passed on both decks with normal release and SIGTERM of the replay reader. Each trial sampled40 output DMA buffers before, during and after the hold. All held samples had zero peaks/RMS. Before/after samples each contained40 distinct buffers with nonzero master audio. Native simulator status (signed16 at snapshot+616, confirmed from StatWatcher::getSimulatorStatus disassembly) changed -1→3→-1. This verifies actual output mute/recovery, not just the selected pad highlight.

| Deck | Release | Master RMS before (L/R) | Held | Master RMS after (L/R) |
|---|---|---|---|---|
|1|Normal|61.54/58.42|0/0|56.89/56.97|
|2|Normal|62.01/61.04|0/0|47.50/50.19|
|1|Reader SIGTERM|60.40/59.88|0/0|54.98/53.07|
|2|Reader SIGTERM|62.21/59.11|0/0|52.88/52.80|

Deck1 cue also muted and recovered; deck2 cue was disabled. Track positions differ between before/after samples, so these numbers demonstrate signal presence, not unchanged gain. Each trial played only its target deck; two-deck isolation was not tested. Research scripts `touch-release-mute-trial.py` and `touch-release-mute-terminated-trial.py`, plus their result JSON files, retain the probes. No runtime code changed. Final state: native PID21886, both banks0, simulator -1, slip flags0, positions stationary300ms at577/427ms, backlight0. Other Release FX actions and physical input remain unverified.

## Rejected MIDI NoteOff no longer releases held touch pads

Reproduced a cross-input fault on both decks with native mode2 pad5 (Slip Loop) and mode6 pad4 (Mute). While touch stayed down, a MIDI Beat Jump press on the same pad key attempted bank3. Native bank selection timed out and correctly suppressed the press. Its subsequent NoteOff nevertheless reached the native player and cleared the touch-held effect in all four cases.

Added `pad-intent.h` to the control adapter: track forwarded tagged presses per deck/pad/bank, suppress orphan and stale-bank releases, and ignore duplicate presses. `test-pad-intent.c` passes locally and on Pi, covering rejected selection, unowned release, duplicate press, deck isolation, late other-bank release and native bank changes. Existing Python pad mapping and held-pad tests also pass. Full Pi build/deployment passed with backup `fbshim-pre-pad-intent.so`.

After restart and native-touch loading of both tracks, all four live overlap trials passed: MIDI NoteOff left Slip Loop held or simulator status3 (Mute) active, and actual touch release cleared the effect. Each trial subsequently produced40 distinct audio DMA buffers with nonzero master output. Research `touch-midi-orphan-before.json` and `touch-midi-orphan-after.json` retain the paired evidence; `touch-midi-orphan-trial.py` now asserts the corrected behavior. Native mode remains the held touch bank because the bank change was rejected; the MIDI action is not queued for later execution. Same-bank source overlap is a separate unverified case.

Post-deployment MIDI Beat Loop regression passed all eight sizes and on/off transitions on both decks, beginning from bank5. Final readback: player PID23095, both banks0, simulator -1 and slip flags0, positions stationary over300ms at4447/4447ms, backlight0.

## Remaining Release FX activation and audio recovery

`touch-release-fx-trial.py` exercised native mode6 pads1,2,3,5,6,7,8 on both decks through the deployed touch bridge. Combined initial and corrected runs cover14 cases. Each held status matched pad number minus one, released status returned to -1, and the recovery audio probe found40 distinct buffers with nonzero master audio. Mute was already covered separately. No runtime code changed.

The trace showed short brake stopping at a fixed position and short backspin moving backward before stopping. Long brake remained in motion during the sampled hold; its full stopping time was not established. Echo Out, Build Up and Ducking had changing audio while active, but these samples do not establish their audible fidelity or exact effect envelopes.

The initial deck1 long-backspin trial failed an overly early audio-presence assertion. Its signed native position reached -2000ms (preroll), and release had advanced only to about -1167ms when sampled. The probe had also incorrectly printed snapshot+620 as unsigned. The corrected probe reads signed time and waits until at least +1500ms before checking recovered music. Both long-backspin trials then passed: native status cleared on release and audio returned as playback advanced out of preroll. This was a test correction, not an audio-engine fix.

Research retains `touch-release-fx-initial.json` (including the failed assertion's data), `touch-release-fx-results.json` (the remaining/corrected cases), and the live trial script. Final state: PID23095, both banks0, simulator -1 and slip flags0, positions stationary over300ms at4447/4447ms, backlight0. Each trial used one playing deck; listening, full-duration holds, physical input and concurrent-deck/effect combinations remain unverified.

## Native-size rotation reduces presenter work

`frame-scale.h` replaces the fullscreen path's1920×1200 intermediate rotation with a1280×800 native-size rotation followed by row-wise nearest scaling directly into scanout. The reversed horizontal axis preserves the old sample phase: output(x,y) reads source(floor(2*y/3),floor(2*(1199-x)/3)). The intermediate frame array is reused as scratch. The nonfullscreen controls layout retains its existing renderer. The presenter now builds with-O3.

`test-frame-scale.c` compares every output pixel to the original mapping using a deterministic32-bit pattern, checks pitch padding and passed local ASan/UBSan plus native Pi tests. With RX3_SCALE_DRM it allocates an offscreen DRM dumb buffer and verifies output there without modesetting. The full new scale/rotation measured6.229ms in that isolated O3 DRM run. An earlier4×4 NEON transpose candidate was slower and was not deployed; exploratory sources remain only in local research.

Live presenter25427 was replaced by26379 without restarting player25426. The running binary is backed up as `/home/pompu_5/rx3-fb-present-pre-native-scale`. Before the change, sampled paused draw times were11.09–11.24ms at59.7–60FPS. After warmup, paused draw time was8.08ms at60FPS. During the subsequent both-decks playback trial, reported intervals ranged8.15–8.63ms and58.7–60FPS, with0–4 late flips per180frames. Each interval accepted180completed snapshots. Actual audio still produced40distinct DMA buffers, with nonzero master/headphone channels; both decks were returned to cue and backlight remained0.

This is a measured reduction in display work with identical pixels, not a verified visible flicker fix or proof of zero dropped refreshes. Native whole-pixel waveform motion, subjective smoothness, physical jog feel and remaining end-to-end checks stay open.

## Touch tempo inside the native Mixer panel

Added one TEMPO% fader per deck to the existing Mixer panel; each deck group now has seven columns. Output/headphone controls, crossfader and cue buttons retain their locations. Tempo uses the native TempoSlider key4109, operation5, signed[-1,1] position, with startup neutral. FLX6 MIDI and touch share the same observed fader state. The number under TEMPO% comes from the native tempo-rate getter, so it reflects the player rather than a fabricated conversion of slider input. A narrow center detent and endpoint snapping accommodate integer touch-calibration rounding.

Local ASan/UBSan tests cover all18controls, layout hit testing, untouched crossfader geometry, invalid tempo values/operations, neutral/endpoints and channel separation. Live touch replay on both decks in the10% range produced exactly+10.00,-10.00 and0.00%; intermediate taps produced+5.05 and-4.90% at their quantized pixel positions. The other deck stayed at zero. Continuous drag updated native tempo; terminating the replay reader while held released the gesture, and the next contact correctly controlled the other deck. Both faders returned to neutral.

Replaying the installed FLX6 mapping at raw12288/4096 gave+5.00/-5.00% and corresponding on-screen fader positions; raw8192 restored both to0.00. After touch tempo changes on loaded tracks, the native player displayed97.7 and88.5BPM from93BPM tracks, with+5.05/-4.90% rates. Actual FLX6 DMA sampled40different buffers and nonzero master/headphone audio. A regression check of the repositioned deck1 LEVEL fader muted master while preserving headphone cue. Its level was restored afterward.

Final live PID26896, both tracks cued at4:43.942 remaining, both tempos0.00%, Mixer closed and backlight0. Previous shim is preserved at runtime `/lib/fbshim-pre-touch-tempo.so`. Screenshots inspected in local research show the new Mixer layout, MIDI feedback and touch-adjusted playback. This adds basic touch tempo control; fine adjustment, touch range/key-lock access and physical comfort remain open.

## Native-step tempo buttons

The Mixer now has minus/plus buttons below each TEMPO fader. They dispatch the existing native slider input at the next native tempo step rather than approximating a step by moving a pixel. RX3 v1.19's STEP_TBL_ at0x41c8b0 specifies0.02% at6%,0.05% at10/16%, and0.5% in Wide100%. `tempo-step.h` chooses the next signed quantization bin, clamps endpoints, and offsets floating-point input within the bin to avoid truncation at a rounding boundary. No synthetic tempo value is displayed; the existing native rate getter remains the numeric source.

`test-tempo-step.c` passed local ASan/UBSan and native Pi builds over every native bin in all four ranges, both directions, endpoints and off-grid zero crossings. Mixer layout tests cover both button pairs and the gaps/boundaries. The buttons consume one gesture through release; there is no repeat-on-hold behavior.

Live touch replay passed48checks: on each deck, in each native range, +step,+2step,+step,zero,-step,zero, with exact native readback and the other deck unchanged. Range selection in this test used the native control queue; touch range selection remains separate work. Both ranges were restored to10%. Screenshot inspection confirmed the button pairs fit beneath their faders; the deck2 footer label moved left to leave room.

After reloading both tracks, a fine increase during deck1 playback reported+0.05% and40different FLX6 DMA buffers (RMS79.70,71.34,317.81,284.34). A minus tap returned native rate to zero while the player remained running. Final playerPID27443: both decks cued, both tempos0%, ranges10%, Mixer closed, backlight0. Previous shim backup: runtime `/lib/fbshim-pre-fine-tempo.so`. Physical touch comfort and behavior during sync/tempo-pickup states remain unverified.

## Touch range and key lock

Each Mixer deck header now contains RANGE and KEY LOCK buttons. RANGE cycles the native TempoRange key4107; KEY LOCK sends the native MasterTempo key4108 with matched press/release. The displayed range and active key-lock color are read from native getters, including changes originating outside the touch adapter. This preserves the existing native tempo semantics rather than maintaining a separate UI toggle state.

Layout tests passed local ASan/UBSan for both deck headers, gutters, boundaries and the existing fine buttons. Live touch replay passed12actions: four range changes and key-lock on/off per deck, with independent native state readback. An additional eight touch range changes at fixed signed slider positions±0.5 produced exactly±8%,±50%,±3%,±5% for16%,Wide,6%,10% respectively. Both original ranges and neutral tempos were restored. Screenshot inspection verified RANGE10% labels and a blue key-lock button matching the native active flag.

Loaded-track playback with both key locks enabled at+5/-5% produced40distinct FLX6 DMA buffers and nonzero master/headphone channels (RMS81.06,71.19,261.83,218.83). Disabling key lock by touch while still playing preserved changing audio (40buffers; RMS76.15,74.30,223.03,224.09). This verifies native control state and audio flow, not an independent measurement of pitch-preservation quality.

Final live PID28039: both tracks cued, tempo0%, range10%, key lock off, Mixer closed and panel brightness0. Prior shim backup: runtime `/lib/fbshim-pre-tempo-options.so`. Physical control comfort, sync/pickup behavior, physical jog feel, visual flicker and reboot validation remain open.

## Sync and tempo pickup investigation

Touch replay toggled the native engine Sync flag while cued and playing in PID28039. Fine tempo and center touches update the native fader rate, but this does not always update effective playback tempo: after Sync was disabled, deck2 retained 97.72 BPM from a 93.07 BPM track while its fader rate reported 0%. A screenshot also showed the retained 97.7 BPM and dimmed 93.0 target. Moving the fader beyond the held rate and back to center restored both actual BPM and the raw fader rate.

The Mixer currently displays `UiGetPlayTempoRate`, which represents the fader setting during pickup. Its fine buttons also use that value. This is an identified UI/control gap, not verified Sync/pickup completion. Read-only disassembly confirms snapshot offsets: effective BPM +20, original BPM +24, tempo target +28, fader rate +34. The earlier research probe labeled +28 as `bpm_raw`; it must not be interpreted as effective BPM.

Playback produced 40 distinct DMA buffers with positive master and headphone RMS. Final state was verified beyond the fader alone: both actual and original BPM 9307, rate 0, Sync off, cued, brightness 0. No runtime changes were deployed in this investigation.

## Separate fader setting and effective BPM

Mixer now labels the percentage FADER % and shows a separate effective BPM from native UiGetPlayBpm (0xfd1fc), including cache invalidation when only BPM changes. ARM build and live deployment passed in PID29019. Both neutral and pickup screenshots were inspected; the display shows +0.00 with 88.4 BPM on deck1 while deck2 shows -5.00 with 88.4 BPM. This reflects native state rather than estimating playback tempo from the fader.

The live trial verified deck1 Sync following deck2: both effective BPM8842, deck1 fader+500, deck2-500, master flagdeck2 and Sync flagdeck1. After Sync off and deck1 fadercenter, its effective BPM stayed8842 while fader became0. Forty distinct DMA buffers, RMS79.48/81.19/223.90/227.11. The initial attempted reproduction synchronized the already-master deck2 and did not create pickup; its assertion failed and cleanup restored both decks. The corrected trial used deck1 as follower.

Final: both cued, actual/original BPM9307, faders0, Syncoff, range10, keylockoff, Mixerclosed, backlight0. Backup runtime/lib/fbshim-pre-bpm-feedback.so. Fine-button takeover remains unresolved; this change makes the separate values visible and does not override native pickup.

## Touch fine tempo after Sync pickup

Live PID29497 adds a native-input catch-up before the fine step when the native tempo target is valid and Sync slave is off. It estimates the held rate from effective/original BPM, rounds to the nearest supported slider bin, dispatches that fader position, then dispatches the requested adjacent bin. It does not clear engine flags or write engine state directly. Invalid BPM and held speeds outside the selected range are refused.

Host ASan/UBSan tests cover every native fine bin, exact 100-BPM pickup bins across all four ranges, the observed 93.07-BPM ±5% cases, invalid inputs and range refusal. Live touch replay passed 16 deck1 pickup cases: plus/minus from each sign at half-range in 6%, 10%, 16%, WIDE. Exact fader targets and released pickup state were checked, with other-deck isolation. The initial WIDE case failed a test's absolute BPM ratio assumption despite reaching the correct -50.50% target; the corrected check measures the one-step BPM delta, within 0.02 BPM of the expected delta. Eight 10/16 cases were captured in command output; the repeated WIDE/6 cases are saved in research/pickup-touch-results.json.

Four deck2 ±5% plus/minus pickup cases also passed. During playback, deck2 fine-plus caught +5% and reached +5.05%, effective BPM9777 versus master9772; 40 distinct DMA buffers, RMS80.33/76.17/202.57/186.86. Final both decks cued, actual/original BPM9307, faders0, range10, keylockoff, Syncoff, Mixerclosed, brightness0. Backup runtime/lib/fbshim-pre-fine-pickup.so.

Remaining limits: held rate estimation uses BPM values rounded to hundredths, not the engine's full-precision tempo. Different-track/off-grid targets, very low BPM, out-of-range live behavior, rapid Sync transitions and physical controller pickup after touch takeover need further verification. These tests do not establish every Sync/pickup case.

## Different-track pickup crossing

Loading Aarena (Knock2 Remix) into deck2 produced original BPM12605 versus Aaliyah9307 on deck1. This exposed a real bug: in WIDE, holding deck2 at9307 then tapping plus from a centered fader changed the raw rate to-2550 but left pickup active and actual BPM9307. The nearest -26% bin had not crossed the actual approximately-26.16% held speed.

The catch-up helper now chooses a bin across the held speed in the direction from the current fader; the requested final fine value still uses the nearest held bin plus/minus one native step. Host ASan/UBSan tests retain all-bin coverage and add both sides of positive/negative different-track targets. Live PID30356 passed12 cases: each deck as follower, starting fader0/+50/-50%, plus and minus. Negative held target reaches-25.5% (93.92 BPM) or-26.5% (92.66 BPM); positive reaches+36% (126.56 BPM) or+35% (125.63 BPM). Pickup is cleared, BPM moves in the requested direction, and the other deck is unchanged.

The final positive-minus case was executed while both decks played and read actual BPM12563/rate3500 on deck1. After resetting its fader, still-running audio yielded40 distinct DMA buffers, RMS84.18/71.12/331.39/276.89; this verifies continued output after the interaction, not audible transition quality. Final both cued, original/actual BPM9307 and12605, faders0, range10, keylockoff, Syncoff, Mixerclosed, brightness0. Backup runtime/lib/fbshim-pre-cross-track.so.

Research results: cross-track-fixed-results.json and cross-track-positive-results.json. The bin crossing can briefly traverse an adjacent native tempo bin before settling; its audible effect and physical MIDI takeover remain unverified. Extreme/very-low BPM, rapid state changes and out-of-range live cases remain open.

## MIDI pickup after touchscreen tempo changes

Pre-fix MIDI replay reproduced both-deck jumps from touch+5.05% to+0.10% on a small hardware-position change near center. The updated bridge tags tempo inputs with extra0x544d. The shim consumes that tag and tracks MIDI ownership per deck; after an untagged touch tempo input, MIDI must approach within two 14-bit increments or cross the last touch target. Accepted MIDI then continues normally until the next touch input. Suppressed MIDI does not alter the native queue or Mixer metadata. Tempo ownership and enqueue order are serialized across input threads.

Host ASan/UBSan tests verify positive/negative crossing, fine target matching, repeated ownership changes, invalid floats, unknown hardware position and independent state. Existing MIDI reconnect/parser tests pass. Live PID30879 passed both signs on both decks: nearby MIDI movement held the touch rate, crossing to an exactly representable ±0.625 normalized input produced ±6.25%, and later MIDI neutral worked. Fine touch+0.05% rejected stationary MIDI0, accepted a crossing MIDI movement and returned to0. The first live test expected exactly-6% from normalized-.6 and failed because 14-bit encoding plus native truncation yields-5.95%; corrected tests use exact-.625.

During deck1 playback, a nearby MIDI movement preserved touch BPM, crossing gave rate625/BPM9888, and 40 distinct DMA buffers had RMS48.55/45.30/193.29/180.32. Final both Aaliyah tracks cued, actual/original BPM9307, faders0, ranges10, keylockoff, Syncoff, Mixerclosed, brightness0. Runtime backup/lib/fbshim-pre-midi-pickup.so; bridge backup/home/pompu_5/flx6-rx3-pre-pickup.py. Updated bridge deployed both to the source checkpoint and the startup script's actual home path; hashes match.

Physical fader feel and pickup guidance remain unverified. The guard tracks normalized fader setting, while native Sync pickup still governs effective speed. Range changes, simultaneous touches/MIDI, reconnect while holding mismatched positions and interactions with active Sync need broader live coverage. No claim of audible smoothness from buffer checks.

## MIDI pickup guidance in the Mixer

Live PID31370 adds amber MATCH FASTER / MATCH SLOWER in each tempo column while the last MIDI position is on the unmatched side of the touch setting. MATCH FADER covers unknown hardware position; matched/owned inputs show FADER %. Labels indicate speed direction, not physical up/down orientation. A small atomic hint snapshot is published after every tempo-input decision, including suppressed MIDI. The Mixer invalidates its paint cache when that hint changes independently of the accepted fader value.

ASan/UBSan helper tests cover unknown/matched/faster/slower states alongside prior ownership checks. Four native screenshots were captured and inspected: unknown startup, neutral matched, simultaneous opposite pickup directions, and caught ±6.25%. Live touch/replay confirmed ±near-center MIDI movements preserved touch+5.05%/-4.90%; crossing inputs acquired ±6.25% and cleared both hints. Final both Aaliyah tracks cued, actual/original BPM9307, faders0, range10, Syncoff, keylockoff, Mixerclosed, brightness0. Backup runtime/lib/fbshim-pre-pickup-hints.so. This pass verified visual and input feedback; audio was not remeasured for this display-only addition.

Research script/result: pickup-hint-trial.py and pickup-hint-results.json; screenshots /tmp/pickup-{unknown,matched,directions,caught}.png. Physical usability, rapid concurrent input, active-Sync/range-change interactions and disconnect-specific hint behavior remain open.

## FLX6 Prepare / Tag List navigation

Read the installed BiteDJ script/XML: VIEW opens Browse, BACK returns to Browse or navigates back, long VIEW (9667) opens Prepare, and SHIFT+VIEW (9668) toggles Prepare membership. Added two bridge bindings, for121 total. RX3 long VIEW opens Tag List with key0203 and stays there on repeated input. Normal VIEW now returns from Tag List to Browse and stays in Browse on repeat. SHIFT+VIEW adds the highlighted track from Browse with420e; within Tag List it emits native long-press operation1 to remove the selected item. This is the native workflow; removing directly from Browse is not implemented as a universal membership toggle.

The first candidate used CmnFunc_CmnInfo_GetTagListWindowDispFlg, but that returned0 while the actual Tag List was visible. The final adapter uses getBrowseMode0x1126d0==4 plus the existing main-panel visibility check. The initial short TagTrack event added but did not remove; native press/long/release0/1/2 removed successfully.

Live final PID32360 passed long-VIEW and normal-VIEW repeated-input sequences. Native screenshots verified an empty Tag List, addition of one Aaliyah track, and removal back to zero items. MIDI parser checks verified all four View/Back variants and release suppression; reconnect/parser tests still pass. Test sequence results are research/prepare-mapping-results.json. Both decks remain loaded/cued at BPM9307, tempo0, range10, keylockoff, Syncoff; player screen restored, brightness0. Runtime backup/lib/fbshim-pre-prepare.so and bridge/home/pompu_5/flx6-rx3-pre-prepare.py. BiteDJ files were only read.

Physical long/shift gesture timing and navigation through other media types remain unverified. Browser acceleration and the full encoder push behavior still require work. Audio was not remeasured for these navigation-only changes.

## FLX6 encoder push navigation

Before this change, MIDI encoder push9641 passed directly to native RotarySelector and stayed on the player screen. The bridge now emits a dedicated4250 intent on press and suppresses release; the control adapter opens Browse from the player or emits paired native RotarySelector press/release within Browse. Existing rotation intent remains separate.

Live PID32643: encoder push opened Browse, BACK shifted focus to the Track sidebar, and push moved into the selected track list. A further push on the track opened Track Menu. MIDI rotation+1 and another push chose Load to Deck1, returning to the player with the track cued. Screenshots /tmp/encoder-{open-browse,back,enter,track-press,loaded}.png inspected. A subsequent touch Play produced40distinct DMA buffers, RMS56.13/51.58/223.82/205.71, then Cue restored the deck.

Final both Aaliyah tracks cued, original/actual BPM9307, rate0, range10, keylockoff, Syncoff; no display enable occurred. Backups runtime/lib/fbshim-pre-encoder-push.so and home/flx6-rx3-pre-encoder-push.py. MIDI reconnect/parser regression passed. Research encoder-push-trial.py/results cover the main/sidebar sequence. Full folder/media navigation, acceleration and physical encoder feel remain unverified.

## Artist/album navigation and deck2 touch cue

Without changing runtime code, exercised a different library route in PID32643: touch Artist category, encoder push into AAMAR, encoder push into SVMMER SVN vol.4, then touch Load2 for Estara. Screenshots confirmed each parent/child page. Touch Mixer, headphone Cue2 and Play2 produced40distinct DMA buffers, RMS62.53/66.36/247.14/261.46, proving both master and cue output for this loaded track. Touch Cue2 returned deck2 to cue; the added headphone selection was toggled off and Mixer closed.

Two FLX6 BACK presses from the track page returned to the album page and then the artist list; screenshots independently verified the titles/selection. Player restored afterward. Final deck1 Aaliyah original/actual BPM9307, deck2 Estara9505, both mode4/cued, faders0, range10, keylockoff, Syncoff. Display remained off. This verifies one nested analysed-library path, not every folder or media type. No code change was needed.

## Touch Tag List and membership controls

Live PID33450 extends the compact navigation surface leftward: six100px cells, native origin680/width600. New physical centers at y30 are Tag List1095 and Tag+/−1245; existing Player1395, Back1545, Source1695, Info1845 remain unchanged. Tag+/− glyphs track native browser mode; painting invalidates when mode changes. Tag List is idempotent while open. Tag− emits native press/long/release for removal. Player uses the Tag List close key when there, returning directly to main instead of stopping at Browse.

Native screenshots and touch replay verified selected-track addition, one-item Tag List, repeat Tag List remaining open, removal to zero items, and Player returning to main. The first candidate Player action returned to Browse; corrected to native0203 in Tag List and final visibility assertion passed. Other main transport/Mixer geometry was unchanged. Final both Aaliyah tracks cued at9307BPM, rate0, range10, keylockoff, Syncoff; brightness0. Backup runtime/lib/fbshim-pre-touch-tags.so. Evidence research/touch-tag-trial.py/results and /tmp/touch-tag-{added,removed,player}.png. Audio was not remeasured for this navigation-only addition.

Physical comfort and behavior of Tag actions in non-track lists/other media contexts remain unverified.

## Player return from Source

The widened toolbar check found Info->Player already working, but Source->Player stopped at Browse. Native Source is browser mode12; its first Browse-key transition is asynchronous and completes after touch release. Two immediately queued presses, and then a release-time second press, both failed live checks.

The final adapter marks a pending return on release. The GUI draw hook observes Source closing, waits three rendered frames outside Source, then queues the final Browse press/release. It cancels if main is already visible, the player screen becomes inactive, or120frames elapse. It does not sleep on the GUI thread.

Live final build passed four touch sequences: Source entered from main, Browse, Tag List and Info, each followed by one Player tap. Every case ended with the main panel visible and browser mode1. Both tracks remained loaded/cued at original BPM9307, tempo0, range10, keylockoff, Syncoff, displayoff. Backup runtime/lib/fbshim-pre-source-player.so. Research source-player-trial.py/results.json. Fast overlapping gestures and stalled-render timeout behavior remain unverified; audio was not remeasured for this navigation change.

## Touchscreen library search

Native Search key0205 opens a working touchscreen keyboard. Added SEARCH as the leftmost compact-navigation button: native origin580/width700 with seven100px cells. Physical Search center945,y30; all six existing button positions remain unchanged. Updated navigation hit indexes and Tag/Source Player special cases accordingly.

Live PID34558 passed a touch-only workflow: Browse, Search, type ESTARA, tap the result to dismiss the keyboard, Load2 from the native information pane, Mixer headphone Cue2, Play2. Search returned Estara by AAMAR, SVMMER SVN vol.4. Native screenshots confirmed the query/result and visible Load buttons. Deck2 loaded original BPM9505; playback yielded40distinct DMA buffers with RMS65.94/70.28/262.48/279.75. Touch Cue2 restored cue, its added headphone selection was removed, and Mixer closed. Search text was cleared through the keyboard and Player returned to main (visibility confirmed).

Final deck1Aaliyah9307/deck2Estara9505, both cued at original tempo, range10, keylockoff, Syncoff. Backup runtime/lib/fbshim-pre-touch-search.so. Research touch-search-trial.py and screenshots /tmp/touch-search-track.png, /tmp/search-estara.png. Long queries, number/symbol layouts, empty/no-match results, physical keyboard feel and other media remain unverified.

## FLX6 tempo-range buttons (2026-09-10)

The installed BiteDJ XML binds 90/91 60 to PioneerDDJFLX6.cycleTempoRange; the RX3 bridge previously ignored these controls. Both now send native TempoRange4107 press/release. Native ranges cycle 6, 10, 16, WIDE100 percent. The mapping now contains123 bindings.

Live player PID34558: replayed the installed XML mappings through the bridge and native queue. Each deck cycled10→16→100→6→10; releases did not advance again, the other deck remained unchanged, and both decks stayed cued at zero tempo. Final state exactly matched the initial probe. Research midi-tempo-range-trial.py includes bounded restoration. This verifies MIDI translation and native behavior, not a physical button press.

Also corrected the stale navigation regression expectation: encoder push now emits one4250 intent, whose native adapter generates paired events, rather than emitting the old raw pair. Navigation and MIDI reconnect tests pass locally; navigation also passed on Pi. Replaced and restarted only the MIDI reader, which opened FLX6 hw:2,0,0 with123 bindings; the native player remainedPID34558 and backlight0. Previous bridge is home/flx6-rx3-pre-midi-range.py. Shifted jogs and remaining unmapped controls are still pending.

## Native loop adjustment through FLX6 (2026-09-10)

Live PID34558, no runtime edits: the installed FLX6 mappings90/91 10 and11 entered/exited native loop-in and loop-out adjustment while looping. Both decks passed. The state probe follows native UiGetPlayLoopInAdjustOn/OutOn (snapshot byte46 bits2/3) and UiGetPlayAdjustTime (snapshot u32+16), verified against disassembly.

During each adjustment, replayed MIDI jog B0/B1 21 through the real Bridge accumulator/tick,24 messages of+10 then24 of-10 at15ms intervals. Native adjustment time increased then decreased for every edge: deck1 IN427→440→420, OUT3007→3014→3000; deck2 IN47→60→40, OUT2572→2580→2567. This proves direction and native loop-edge movement, not calibrated physical sensitivity or exact reversible movement. Native loop beat ratio became0/0 after manual adjustment. Loop points were changed by this trial; cleanup exited loops and adjustment, cued both decks and restored Hot Cue mode, rather than restoring original loop boundaries.

Research loop-adjust-jog-trial.py and loop-adjust-jog-results.jsonl retain the trial. Both ordinary buttons already support native edge editing; the unmapped BiteDJ shifted toggleLoopAdjustIn/Out require an active-loop guard because native IN/OUT can also create loop points outside a loop. No shifted mapping was added on this evidence alone. Physical jog feel, shift transitions and loop-edit touchscreen access remain incomplete. Backlight stayed0 and native PID unchanged.

## FLX6 SHIFT+BROWSE waveform zoom (2026-09-10)

BiteDJ XML B6 64 waveformZoom was previously ignored. The bridge now emits a dedicated425a native rotary intent on channel0: value127 increments the shared native zoom index, value1 decrements it; zero and other values are ignored. The native adapter only forwards it while player_screen_active and main_panel_visible; ordinary B6 40 remains browser navigation.124 bindings are active.

Built the combined ARM32 shim and deployed with a clean player stop. Live PID35221: both Aaliyah tracks loaded by touch, zoom2→3→2 through the actual installed XML/bridge; ordinary encoder opened Browse. SHIFT+BROWSE inputs in Browse left zoom2 and the library row/control pixels unchanged. Initial whole-list pixel comparison failed on the selected title marquee; inspected both screenshots and excluded only its title rectangle from the revised comparison. Other list pixels, row indicators and load controls were compared. Research midi-zoom-trial.py retains the trial. Zoom direction versus physical feel still needs owner verification.

Host navigation regression includes both zoom directions, channel0 normalization and ignored zero/neutral values; navigation and MIDI reconnect tests passed. Backups home/flx6-rx3-pre-shift-zoom.py and runtime/lib/fbshim-pre-shift-zoom.so. Both decks returned to cue, range10, tempo0, Syncoff, backlight0. This does not fix waveform flicker or complete shifted jog/LED/FX/touchscreen coverage.

Post-deployment touch Play1 produced40distinct FLX6 DMA buffers, RMS54.87/49.74/218.85/198.25 across master/headphone channels; touch Cue1 restored playback state4. This verifies nonzero output after the shim rebuild, not perceived audio quality.

## Guard zoom input while native GRID mode is active (2026-09-10)

Touchscreen investigation found that a1.2second hold on native ZOOM at physical1752,597 enters GRID editing. The same hold exits it. A short tap on GRID1845,597 did not switch modes. Confirmed the visible blue GRID label and red grid markers; CmnFunc_CmnInfo_GetGridAdjustModeFlg0x17f8a0 reads u32 at0x03253564+0x1538, which changed0→1→0 consistently with screenshots.

SHIFT+BROWSE's new425a intent now also rejects input while that native grid flag is set. The generic rotary key is context-dependent; this prevents a dedicated zoom input being forwarded to grid editing. Previous main-window-only guard was incomplete. No grid-edit input was deliberately tested before the fix.

Built/deployed combined ARM32 shim. Live PID35703, both Aaliyah tracks loaded through touch: entered GRID via touch hold, replayed each SHIFT+BROWSE direction separately, confirmed zoom2/grid1 and pixel-identical waveform/grid regions after each. Exited GRID by touch hold and verified normal zoom2→3→2. Finalgrid0,main mode1. Research zoom-grid-guard-trial.py and grid-mode-probe.py retain the assertions. Backupruntime/lib/fbshim-pre-zoom-grid-guard.so. Touchscreen zoom buttons were not added this turn; they remain pending along with other incomplete controls.

Post-build touch Play1 yielded40distinct audio buffers, RMS55.57/50.68/221.59/202.03 on FLX6 master/headphone channels. Touch Cue1 restored both decks to state4; rate0/range10/Syncoff, backlight0. BiteDJ unchanged.

## Touchscreen zoom buttons (2026-09-10)

Added native DS_GR window5 with ZOOM−/+ at x1090,y354,width180,height28, in the blank space above the original ZOOM/GRID selector. The buttons do not cover the waveform panels or replace that selector. They appear only on the player screen with Mixer closed and GRID mode off. Shared native-zoom-layout.h defines draw/hit geometry; one touch gesture emits one native rotary step, consuming motion/hold until release. They are added touch controls driving native RX3 functions, not original Pioneer touchscreen widgets.

Built/deployed ARM32 shim. Live PID36012: touch replay plus2→3,minus3→2,1.2second held plus2→3 only once,minus3→2. GRID entry hides buttons; touches at their former locations leave zoom/grid unchanged; leaving GRID restores them. Mixer also hides them. Screenshot native-touch-zoom.png inspected with both waveforms and the original selector unobscured. During the first Mixer trial, taps at the former zoom positions reached the Mixer filter/tempo controls as expected; deck2filter and tempo were explicitly restored to.5/0. The retained trial avoids those unrelated Mixer slider taps. Physical target comfort and all screen variants remain unverified.

Backup runtime/lib/fbshim-pre-touch-zoom.so. User reiterated that their installed BiteDJ FLX6 mapping contains their preferred behavior: use it as the authority, preserve it, and disclose native limitations instead of silently substituting RX3 defaults. The new controls here are touchscreen additions; FLX6 mappings unchanged this turn.

Post-build touch playback produced40distinct audio buffers, RMS55.73/52.11/222.16/207.72 on master/headphones. Returned both decks to cue, rate0/range10/Syncoff and backlight0.

## Match BiteDJ Shift/scratch cancellation (2026-09-10)

Refreshed the actual installed FLX6 XML/script read-only. Script SHA256b544f6d1746e89e57d090fc897b7fcaed141d582d66de46d1a406a7b1bdb33d0; XML1df86863293b8c9eb48d1748b6a3e4bd56b2a4f21c5f08c3b5b83bc101fb0301. BiteDJ shiftPressed explicitly cancels scratching; shifted jogSearch translates the beatgrid and does not fast-seek. Its tempoRanges are6/10/16/25percent, whereas native RX3 currently cycles6/10/16/WIDE100. Those are explicit remaining parity gaps.

Bridge now tracks Shift separately per deck. Shift press stops pending jog motion and releases native JogTouch before forwarding Shift. While Shift is held, ordinary jog rotation/touch is suppressed; grid translation is still unmapped. Normal touch works again after Shift release. Reader cleanup clears Shift state. This is scratch behavior parity only, not completion of SHIFT+jog.

Host/Pi test-shift-jog.py passes both decks, overlap ordering, suppressed rotation/touch, other-deck independence, resumed scratch, and cleanup/reset. Host navigation and MIDI reconnect regressions also passed. Live PID36012: actual installed mapping through Bridge/native FIFO while each deck played; native snapshot byte46bits4/5 (confirmed StatWatcher getters) showed touch/scratch1/1 beforeShift,0/0 afterShift and during shifted replay,1/1 after release/re-touch. Finaltouch/scratch0/0 and play4 on both decks. Research shift-jog-live-trial.py retains the sequence. Physical gesture timing and beatgrid translation remain unverified.

Deployed by restarting MIDI reader only; native player unchanged. Backuphome/flx6-rx3-pre-shift-scratch.py. Both decks cued,rate0,range10,Syncoff,backlight0. BiteDJ files unchanged.

## SHIFT+jog native beatgrid translation (2026-09-10)

BiteDJ source on Pi (piflex-source-ee55091a69/src/engine/controls/bpmcontrol.cpp318 onward) converts each beats_translate_move step to sampleRate*0.01/stereoChannels =5ms. Installed FLX6 script accumulates(value−64)/16 and truncates towardzero, clearing residual on Shift changes. Bridge matches that arithmetic using integer ticks. Dedicated B0/B1 29 and ordinary jog packets while Shift is held now send internal grid intent4744; neither uses scratch movement.126 mappings loaded.

New native-grid.c queues bounded commands from the FIFO reader to the GUI render thread. Commands carry the loaded track’s8-byte music identity; changed identity, inactive application or native GridAdjustMode_ValidChk failure rejects the command. On the GUI thread, save active deck, select the MIDI deck, call native GridAdjust0x133744, restore prior deck. The native function retains its validity checks, limits, offset renewal and database notification path. Queue overflow drops new commands; live rapid-load/overflow races remain unverified.

Initial offset-unit assumption was wrong:100RX3 units moved red grid lines3–4pixels at95.05BPM, compared with≈95pixels per beat. Corrected conversion to20quarter-millisecond RX3 units per5ms BiteDJ nudge. After correction,20nudges (400units/100ms) moved markers505/600/695/789/884/979 to520/615/710/805/899/994 (one line rounded804 in the captured pair); reverse returned original columns exactly. Research corrected-results retains exact columns.

Live PID36675, Aaliyah deck1 and Estara deck2:15ticks nochange,16thtick offset+20, reverse through0to−20 then0. On each deck, the other offset, active deck2, GRID mode0, cue state4, position fields, BPM and touch/scratchbits were unchanged. Visible GRID trial confirmed actual rendered marker movement and reversal. Load2 request after+20 still showed20, but this does not prove a fresh reload or disk persistence; full restart persistence remains pending. All trial offsets restored0. Post-build touch Play1 yielded40distinct DMA buffers, RMS56.68/54.34/225.06/215.80 on master/headphones, then Cue1 restored pause. Physical jog feel, playback-time grid changes, native boundary behavior and persistence are not fully verified.

Before edits, stopped RX3 and copied3.9GB test-library rekordbox and USBANLZ metadata to /home/pompu_5/rx3-grid-recovery-20260910; export.pdb byte comparison passed before restart. Original USB1 remains read-only; BiteDJ files unchanged. Runtime backup/lib/fbshim-pre-grid-jog.so; bridge home/flx6-rx3-pre-grid-jog.py. Final both tracks cued,rate0,range10,Syncoff,GRIDoff,backlight0. Host grid-quantum, Shift/scratch, navigation and reconnect tests passed. Preferred25% tempo range remains pending.

## Grid persistence failure isolated and test edit restored (2026-09-10)

A full restart disproved persistence outside GRID: PID36675 Estara deck2 offset0→20, clean restart and touch reload intoPID37123 returned0. Repeated in native GRID mode (1.2s hold at1752,597, wait1s, nudge20, wait2s, exitGRID,wait2s), restarted/reloaded intoPID37349 and offset20 survived. Therefore native save works; the new jog adapter bypasses the GRID save lifecycle. Its direct GridAdjust call is insufficient for persistent edits outsideGRID.

Restored−20 inside native GRID mode, exited and waited for save; a third clean restart/touch reload intoPID37572 read offset0. Both Aaliyah/Estara remain cued,tempo0,range10,Syncoff,backlight0. Modified-metadata comparison against recovery snapshot found export.pdb/exportExt.pdb and USBANLZ/P055/00014A79/ANLZ0000.DAT changed in size or timestamp. Native GridAdjustCycleCheck0x133bdc uses GRID session state, music identity, per-deck save flags0x100 and an approximately700ms idle threshold. Detailed trace/next-step constraints are in research/GRID-PERSISTENCE.md; grid-persistence-load.py retains restart reload/probe workflow.

No runtime code changed this turn. Updated README to explicitly state that outside-GRID jog edits are temporary. Automatic save integration and alternating-deck/track-change handling remain required; do not treat same-process reload as persistence proof. BiteDJ and original read-onlyUSB1 unchanged.

## Save SHIFT+jog edits outside native GRID mode (2026-09-10)

The adapter now wraps GridAdjust with the native GRID save lifecycle when the visible GRID mode is off. On the GUI thread, select the intended MIDI deck, enable the native grid flag, call GridAdjustCycleCheck to capture identity/state, apply GridAdjust, cycle again, clear the flag, cycle to commit, then restore active deck. The flag is restored within the callback before the next render. If GRID was already active, its existing save lifecycle remains responsible; cross-deck edits while another deck is selected in visible GRID still require verification.

Only one queued grid command is applied per render interval because the native save request uses shared staging storage. This spaces requests but is not a formal worker-acknowledgment mechanism; heavy-I/O stress, queue overflow and abrupt termination during save remain unverified. Existing track-identity/native-validity checks are preserved.

Built/deployed combined ARM32 shim, backup/lib/fbshim-pre-grid-save.so. PID37857, Aaliyah/Estara, GRIDoff and active deck2: an immediate burst of8alternating commands produced offsets+80/−80 without changing GRID or active selection. Clean player stop/restart, touch reloaded both tracks intoPID38066, offsets+80/−80 survived. This verifies both-deck save persistence for that burst, addressing the prior session-only failure. Research grid-save-restart-trial.py and grid-persistence-load.py retain the actions/probes. Grid quantum and Shift/scratch parser regressions passed locally.

Restoration verification: PID38066 restored both offsets to0 through the new outside-GRID path. After another clean restart/touch reload, PID38263 read offsets0/0,GRID0,active deck2. Both modified analysis DATs (P035/00002653 and P055/00014A79) were byte-identical to the recovery-snapshot copies. Post-restart playback check completed separately below. BiteDJ and read-only original USB1 unchanged.
