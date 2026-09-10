#ifndef RX3_AUDIO_RECOVERY_H
#define RX3_AUDIO_RECOVERY_H
#include <stdint.h>
/* Caller serializes every operation, including PCM writes. No worker thread.
 * open_configured must apply the saved hardware AND software configuration.
 * On error it may return a partial handle, which this controller will close.
 * The callback must not publish handles or recursively call this controller. */
struct rx3_audio_driver {
 void *context;
 int (*open_configured)(void *,int output,void **handle);
 void (*close)(void *,void *handle);
};
enum rx3_audio_pair_state {RX3_AUDIO_STOPPED,RX3_AUDIO_LIVE,RX3_AUDIO_OFFLINE};
struct rx3_audio_pair {
 struct rx3_audio_driver driver;
 void *pcm[2]; /* 0 master, 1 headphones; both live or both null */
 enum rx3_audio_pair_state state;
 uint64_t next_retry_ms;
 int last_error;
};
/* Takes ownership only if both configured handles and callbacks are valid. */
int rx3_audio_pair_init(struct rx3_audio_pair *,struct rx3_audio_driver,void *,void *);
/* Device loss on either output invalidates the entire shared hardware pair. */
void rx3_audio_pair_lost(struct rx3_audio_pair *,uint64_t now_ms,int error);
/* 1 ready, 0 still offline/stopped. now_ms is a monotonic clock. No sleeping,
 * PCM writes, or simulated-success frame counts; the caller handles pacing. */
int rx3_audio_pair_retry(struct rx3_audio_pair *,uint64_t now_ms);
void rx3_audio_pair_stop(struct rx3_audio_pair *);
#endif
