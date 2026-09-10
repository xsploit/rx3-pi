# Audio recovery investigation

Status: the pair-reopen controller is implemented and tested in isolation; live reconnect is not integrated or verified. This is distinct from the working MIDI rediscovery loop. The live player was left running and paused; no USB device was detached and no native audio error was injected.

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

Before live detach testing, use isolated fake ALSA transport to exercise failure during either output, persistent absence, reopen failure, card-number changes, parameter failure, cleanup and successful recovery. Then verify actual master/cue audio after reconnect while retaining loaded tracks and touch responsiveness. The isolated pair-lifecycle checks below now pass. Real ALSA configuration, write-error handling, pacing and live reconnect gates remain open.

Local research contains `alsa-thread-disasm.txt` and `alsa-parameters-disasm.txt` from the live executable. No runtime code was changed in this investigation.

## Pair-reopen controller (not deployed)

`audio-recovery.c/.h` owns the master/cue pair and coordinates device-loss cleanup and reopening. Either output losing the hardware invalidates both handles. Repeated loss reports do not restart the retry clock. Failed attempts are separated by at least1000ms measured from their start. Replacements become available only after both `open_configured` callbacks succeed; a failed callback's partial handle and any completed sibling are closed. Stop prevents further reopening and closes remaining handles exactly once.

The caller must serialize writes, close and controller operations. Driver callbacks must be bounded and must restore the saved hardware/software configuration. The controller does not call ALSA, sleep, generate audio, or claim discarded frames were played. It is intentionally absent from `build.sh` until the ALSA adapter and pacing logic are implemented.

`test-audio-recovery.c` passed with local AddressSanitizer/UndefinedBehaviorSanitizer and as a statically linked ARM32 executable on the Pi. It exercises persistent absence, one-second retry gating under repeated callbacks, duplicate loss reports, failure configuring either output, success with a null handle, simulated card-number change, successful pair replacement, offline stop and live stop. The fake driver checks that neither replacement is published while configuration is incomplete and that cleanup leaks no handles. This is lifecycle evidence, not proof that real ALSA parameters or USB devices recover.

Local test:

```sh
gcc -std=c11 -O2 -Wall -Wextra -Werror -fsanitize=address,undefined -o /tmp/test-audio-recovery audio-recovery.c test-audio-recovery.c
/tmp/test-audio-recovery
```

Next integrate a driver that saves/restores real ALSA parameters, resolves stable caller handles to replacements, distinguishes recoverable errors from device loss, and provides paced unavailable output. Keep the vendor DMA error path unreachable for managed output errors. Then test the adapter before any live USB detach.
