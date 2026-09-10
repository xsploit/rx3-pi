# Audio recovery investigation

Status: reconnect is not implemented or verified. This is distinct from the working MIDI rediscovery loop. The live player was left running and paused; no USB device was detached and no native audio error was injected.

## Verified native error path

Disassembly of the deployed RX3 v1.19 player, `juce::ALSAThread::run()` at0x3c52e8:

- Playback calls `snd_pcm_writei`. Negative results other than -32 and -86 enter0x3c55f8. These two special values bypass this branch; the playback branch does not itself call `snd_pcm_prepare` for them.
- The error branch prints `ALSA: wait Resolving xrun`, opens `/dev/mem`, and attempts a44-byte mapping at physical address0x020ec000. It polls offset40, then retries the existing loop. This is vendor DMA recovery, not USB sound-device reopening.
- Failed `/dev/mem` open prints a memory-device error and returns to the loop without the one-second delay used by the failed-mmap branch. Repeated device errors could therefore produce repeated logging; that behavior has not been induced live.
- `/dev/mem` is absent inside the current Pi runtime. Do not provide physical memory access to make this vendor path run.
- Capture read errors have separate `snd_pcm_prepare` branches for -32; that does not establish playback-device reconnect.

The native loop contains no PCM close/open sequence in this error path. The current shim redirects PCM open/configuration but does not wrap `snd_pcm_writei`, `snd_pcm_prepare` or `snd_pcm_close`. The existing `start-rx3.sh` only starts a new player when its process is absent, so a surviving process with failed audio is not repaired by repeating start.

## Current audio topology

Master and headphone PCMs are separate `rx3out` and `rx3cue` plug/route handles sharing one four-channel `rx3mix` dmix hardware stream. The device name uses `hw:CARD=DDJFLX6,DEV=0`; this avoids a fixed card number at open time but does not replace an already-open disconnected handle. On inspection the controller was present as card2, the MIDI reader had119 bindings, and player PID23095 was live.

`juce::ALSADevice::setParameters()` at0x3c68b4 configures access, format, rate, channels, period count/size and hardware params, then sets silence/start/stop software thresholds. A reconnect implementation needs both hardware and software configuration, not just a new `snd_pcm_open` call. The shim forces interleaved access and currently routes master/headphones at0.25 gain per channel.

## Next implementation boundary

Intercept playback errors before the vendor DMA branch, distinguish recoverable underrun/suspend from device loss, and coordinate replacing both output handles and their configuration. All subsequent prepare/close calls must resolve to the replacement handle. Bound retries and pace output while hardware is absent; avoid a busy loop. Preserve native track/deck state and report audio unavailability rather than silently claiming playback success.

Before live detach testing, use isolated fake ALSA transport to exercise failure during either output, persistent absence, reopen failure, card-number changes, parameter failure, cleanup and successful recovery. Then verify actual master/cue audio after reconnect while retaining loaded tracks and touch responsiveness. This document records the design constraints; none of those recovery gates has passed yet.

Local research contains `alsa-thread-disasm.txt` and `alsa-parameters-disasm.txt` from the live executable. No runtime code was changed in this investigation.
