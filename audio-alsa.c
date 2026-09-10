#define _GNU_SOURCE
#include "audio-alsa.h"
#include <dlfcn.h>
#include <errno.h>
#include <string.h>
#ifdef RX3_AUDIO_PROXY_TEST
#include <stdio.h>
#endif
static void free_saved(struct rx3_alsa_saved *s){
 if(s->hw)snd_pcm_hw_params_free(s->hw);
 if(s->sw)snd_pcm_sw_params_free(s->sw);
 *s=(struct rx3_alsa_saved){0};
}
int rx3_alsa_driver_init(struct rx3_alsa_driver *d){
 *d=(struct rx3_alsa_driver){0};
 /* Direct calls would re-enter the PCM redirection/configuration wrappers. */
 d->open_real=dlsym(RTLD_NEXT,"snd_pcm_open");
 d->close_real=dlsym(RTLD_NEXT,"snd_pcm_close");
 d->hw_real=dlsym(RTLD_NEXT,"snd_pcm_hw_params");
 d->sw_real=dlsym(RTLD_NEXT,"snd_pcm_sw_params");
 return d->open_real&&d->close_real&&d->hw_real&&d->sw_real?0:-ENOSYS;
}
int rx3_alsa_save(struct rx3_alsa_driver *d,int output,snd_pcm_t *pcm,const char *name,int mode){
 if(output<0||output>1||!pcm||!name||!*name)return -EINVAL;
 if(strlen(name)>=sizeof(d->saved[0].name))return -ENAMETOOLONG;
 if(snd_pcm_stream(pcm)!=SND_PCM_STREAM_PLAYBACK)return -EINVAL;
 struct rx3_alsa_saved next={.mode=mode};int result;
 strcpy(next.name,name);
 if((result=snd_pcm_hw_params_malloc(&next.hw))<0)goto fail;
 if((result=snd_pcm_sw_params_malloc(&next.sw))<0)goto fail;
 if((result=snd_pcm_hw_params_current(pcm,next.hw))<0)goto fail;
 if((result=snd_pcm_sw_params_current(pcm,next.sw))<0)goto fail;
 free_saved(&d->saved[output]);d->saved[output]=next;return 0;
fail:
 free_saved(&next);return result;
}
/* hw_params_current contains plugin-specific constraints and cannot be replayed
 * onto a fresh plug/route/dmix handle. Rebuild the negotiated settings from a
 * fresh constraint space instead of copying that opaque object. */
static int rebuild_hw(snd_pcm_t *pcm,const snd_pcm_hw_params_t *saved,snd_pcm_hw_params_t *hw){
 snd_pcm_access_t access;snd_pcm_format_t format;snd_pcm_subformat_t subformat;
 unsigned channels,rate;snd_pcm_uframes_t period,buffer;int result,dir;
#define CHECK(call) do { if((result=(call))<0)return result; } while(0)
 CHECK(snd_pcm_hw_params_get_access(saved,&access));
 CHECK(snd_pcm_hw_params_get_format(saved,&format));
 CHECK(snd_pcm_hw_params_get_subformat(saved,&subformat));
 CHECK(snd_pcm_hw_params_get_channels(saved,&channels));
 CHECK(snd_pcm_hw_params_get_rate(saved,&rate,&dir));
 CHECK(snd_pcm_hw_params_get_period_size(saved,&period,&dir));
 CHECK(snd_pcm_hw_params_get_buffer_size(saved,&buffer));
 CHECK(snd_pcm_hw_params_any(pcm,hw));
 CHECK(snd_pcm_hw_params_set_access(pcm,hw,access));
 CHECK(snd_pcm_hw_params_set_format(pcm,hw,format));
 CHECK(snd_pcm_hw_params_set_subformat(pcm,hw,subformat));
 CHECK(snd_pcm_hw_params_set_channels(pcm,hw,channels));
 CHECK(snd_pcm_hw_params_set_rate(pcm,hw,rate,0));
 CHECK(snd_pcm_hw_params_set_period_size(pcm,hw,period,0));
 CHECK(snd_pcm_hw_params_set_buffer_size(pcm,hw,buffer));
#undef CHECK
 return 0;
}
static int reopen(void *ctx,int output,void **handle){
 struct rx3_alsa_driver *d=ctx;*handle=0;
 if(output<0||output>1||!d->open_real||!d->hw_real||!d->sw_real)return -EINVAL;
 struct rx3_alsa_saved *s=&d->saved[output];
 if(!s->hw||!s->sw)return -EINVAL;
 snd_pcm_t *pcm=0;
 int result=d->open_real(&pcm,s->name,SND_PCM_STREAM_PLAYBACK,s->mode|SND_PCM_NONBLOCK);
 *handle=pcm; /* Pair controller owns cleanup, including partial failures. */
 if(result<0)return result;
 /* Rebuild hardware constraints on the new handle; keep both saved parameter
  * objects unchanged for later retry attempts. */
 snd_pcm_hw_params_t *hw=0;snd_pcm_sw_params_t *sw=0;
#ifdef RX3_AUDIO_PROXY_TEST
 const char *stage="allocate";
#endif
 if((result=snd_pcm_hw_params_malloc(&hw))<0)goto done;
 if((result=snd_pcm_sw_params_malloc(&sw))<0)goto done;
 snd_pcm_sw_params_copy(sw,s->sw);
 #ifdef RX3_AUDIO_PROXY_TEST
 stage="hardware parameters";
#endif
 if((result=rebuild_hw(pcm,s->hw,hw))<0)goto done;
 if((result=d->hw_real(pcm,hw))<0)goto done;
 #ifdef RX3_AUDIO_PROXY_TEST
 stage="software parameters";
#endif
 if((result=d->sw_real(pcm,sw))<0)goto done;
 #ifdef RX3_AUDIO_PROXY_TEST
 stage="blocking mode";
#endif
 result=snd_pcm_nonblock(pcm,!!(s->mode&SND_PCM_NONBLOCK));
done:
#ifdef RX3_AUDIO_PROXY_TEST
 if(result<0)fprintf(stderr,"RX3 test reopen output %d failed at %s: %d\n",output,stage,result);
#endif
 if(hw)snd_pcm_hw_params_free(hw);
 if(sw)snd_pcm_sw_params_free(sw);
 return result;
}
static void close_pcm(void *ctx,void *handle){
 struct rx3_alsa_driver *d=ctx;d->close_real(handle);
}
struct rx3_audio_driver rx3_alsa_pair_driver(struct rx3_alsa_driver *d){
 return (struct rx3_audio_driver){d,reopen,close_pcm};
}
void rx3_alsa_driver_destroy(struct rx3_alsa_driver *d){
 for(int i=0;i<2;i++)free_saved(&d->saved[i]);
}
