#ifndef RX3_AUDIO_PACER_H
#define RX3_AUDIO_PACER_H
#include <stdint.h>
/* One equal-size write per output per engine block, as in the RX3 loop.
 * Caller serializes access, supplies a monotonic clock, and sleeps until the
 * returned absolute deadline only for RETRY/UNAVAILABLE writes. Scheduling
 * delays up to100ms retain the timeline; larger backlogs reset it. Reset when
 * leaving offline mode or changing rate/block size. No sleeping in this API. */
struct rx3_audio_pacer {
 uint64_t deadline_ns,remainder;
 unsigned rate,frames,seen;
 int started;
};
int rx3_audio_pacer_init(struct rx3_audio_pacer *,unsigned rate,unsigned frames);
/* Returns 0 for invalid output/uninitialized configuration. Master=0,cue=1.
 * Repeated writes from just one output still advance the clock. */
uint64_t rx3_audio_pacer_deadline(struct rx3_audio_pacer *,int output,uint64_t now_ns);
#endif
