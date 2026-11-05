# DDJ-FLX4 RX3 input profile

`Pioneer-DDJ-FLX4.rx3.xml` contains the MIDI addresses for controls the RX3
bridge can translate. Address and high-resolution CC-pair reference:
https://github.com/mixxxdj/mixxx/blob/2.5/res/controllers/Pioneer-DDJ-FLX4.midi.xml

Jog encoding (value minus 64) and 720 ticks/revolution reference:
https://github.com/mixxxdj/mixxx/blob/2.5/res/controllers/Pioneer-DDJ-FLX4-script.js

This is an RX3 input profile, not a complete Mixxx preset. It does not load
JavaScript. The controller ID selects the FLX4 bridge aliases and jog resolution;
FLX6 profiles retain their existing behavior.

Included: both decks' load, play/cue, loop in/out/reloop, sync/leader, quantize,
tempo/range, jog touch/turn; browse/back/push/zoom; channel gain, EQ, faders,
filter, headphone cue/mix, crossfader; eight hot cues, beat loops and default
beat-jump pads on each deck. Browse sends one RX3 step per MIDI encoder step.
Shift+jog retains the bridge's existing grid-edit behavior.

Not included: LED feedback, sampler, Pad FX, Beat FX, smart functions, memory-cue
navigation, loop endpoint adjustment with the jog, hot-cue deletion, changing
beat-jump pad sizes, or exact rekordbox acceleration/seek behavior. Quantize and
player/audio latency are unchanged. Mapping success does not certify hardware
playback or either deck's audio routing.

Tests replay the shipped profile's MIDI bytes through the bridge for both decks,
high-resolution faders, pads/releases, browsing and jog scaling. Physical testing
is still required. Restart RX3 after changing mapping or bridge code.
