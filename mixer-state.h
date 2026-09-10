#ifndef RX3_MIXER_STATE_H
#define RX3_MIXER_STATE_H
#include <stdint.h>
#define RX3_MIXER_COUNT 16
struct rx3_mixer_binding {int key,channel;};
extern const struct rx3_mixer_binding rx3_mixer_bindings[RX3_MIXER_COUNT];
/* Last dispatched input values, not an acknowledgement from the audio engine. */
struct rx3_mixer_snapshot {float levels[RX3_MIXER_COUNT];uint32_t valid,cue,revision;};
void rx3_mixer_observe(int key,int operation,int channel,float value);
int rx3_mixer_snapshot(struct rx3_mixer_snapshot *out);
void rx3_dispatch_key(void *manager,int key,int operation,int channel,long value,float analog,long extra);
#endif
