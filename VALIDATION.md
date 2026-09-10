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
