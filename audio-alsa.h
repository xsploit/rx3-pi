#ifndef RX3_AUDIO_ALSA_H
#define RX3_AUDIO_ALSA_H
#include <alsa/asoundlib.h>
#include "audio-recovery.h"
struct rx3_alsa_saved {
 char name[128];int mode;
 snd_pcm_hw_params_t *hw;
 snd_pcm_sw_params_t *sw;
};
struct rx3_alsa_driver {
 struct rx3_alsa_saved saved[2];
 int (*open_real)(snd_pcm_t **,const char *,snd_pcm_stream_t,int);
 int (*close_real)(snd_pcm_t *);
 int (*hw_real)(snd_pcm_t *,snd_pcm_hw_params_t *);
 int (*sw_real)(snd_pcm_t *,snd_pcm_sw_params_t *);
};
/* Initialize fresh storage; resolve real ALSA entry points past the shim. */
int rx3_alsa_driver_init(struct rx3_alsa_driver *);
/* Snapshot a fully configured playback PCM. A failed capture preserves the
 * previous snapshot. Does not own or close the supplied native PCM handle. */
int rx3_alsa_save(struct rx3_alsa_driver *,int output,snd_pcm_t *,const char *name,int mode);
struct rx3_audio_driver rx3_alsa_pair_driver(struct rx3_alsa_driver *);
/* Stop the pair first. Free snapshots only; caller still owns live PCMs. */
void rx3_alsa_driver_destroy(struct rx3_alsa_driver *);
#endif
