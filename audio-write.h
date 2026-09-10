#ifndef RX3_AUDIO_WRITE_H
#define RX3_AUDIO_WRITE_H
#include "audio-recovery.h"
enum rx3_audio_write_state {RX3_AUDIO_PROGRESS,RX3_AUDIO_RETRY,RX3_AUDIO_UNAVAILABLE,RX3_AUDIO_CLOSED};
struct rx3_audio_write_result {
 enum rx3_audio_write_state state;
 long frames; /* Actual accepted frames only, never a simulated success. */
 int error;
};
struct rx3_audio_writer {
 void *context;
 long (*write)(void *,void *pcm,const void *samples,unsigned long frames);
 int (*prepare)(void *,void *pcm);
 int (*resume)(void *,void *pcm); /* Optional; unavailable resume uses prepare. */
};
/* Caller serializes with all pair operations and paces RETRY/UNAVAILABLE.
 * Callbacks must be bounded: this function performs at most two writes and
 * one resume/prepare recovery sequence. Handles come from the current pair. */
struct rx3_audio_write_result rx3_audio_write(struct rx3_audio_pair *,
 const struct rx3_audio_writer *,int output,const void *samples,
 unsigned long frames,uint64_t now_ms);
#endif
