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
