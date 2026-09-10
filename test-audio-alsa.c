#include "audio-alsa.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
struct settings {
 unsigned rate,channels;
 snd_pcm_format_t format;snd_pcm_access_t access;
 snd_pcm_uframes_t period,buffer,start,stop,silence_threshold,silence_size;
};
static struct settings inspect(snd_pcm_t *pcm){
 snd_pcm_hw_params_t *hw;snd_pcm_sw_params_t *sw;struct settings s={0};
 assert(snd_pcm_hw_params_malloc(&hw)==0&&snd_pcm_sw_params_malloc(&sw)==0);
 assert(snd_pcm_hw_params_current(pcm,hw)==0&&snd_pcm_sw_params_current(pcm,sw)==0);
 assert(snd_pcm_hw_params_get_rate(hw,&s.rate,0)==0);
 assert(snd_pcm_hw_params_get_channels(hw,&s.channels)==0);
 assert(snd_pcm_hw_params_get_format(hw,&s.format)==0);
 assert(snd_pcm_hw_params_get_access(hw,&s.access)==0);
 assert(snd_pcm_hw_params_get_period_size(hw,&s.period,0)==0);
 assert(snd_pcm_hw_params_get_buffer_size(hw,&s.buffer)==0);
 assert(snd_pcm_sw_params_get_start_threshold(sw,&s.start)==0);
 assert(snd_pcm_sw_params_get_stop_threshold(sw,&s.stop)==0);
 assert(snd_pcm_sw_params_get_silence_threshold(sw,&s.silence_threshold)==0);
 assert(snd_pcm_sw_params_get_silence_size(sw,&s.silence_size)==0);
 snd_pcm_hw_params_free(hw);snd_pcm_sw_params_free(sw);return s;
}
static snd_pcm_t *configured(int output){
 snd_pcm_t *pcm;assert(snd_pcm_open(&pcm,"null",SND_PCM_STREAM_PLAYBACK,0)==0);
 snd_pcm_hw_params_t *hw;snd_pcm_sw_params_t *sw;
 assert(snd_pcm_hw_params_malloc(&hw)==0&&snd_pcm_sw_params_malloc(&sw)==0);
 assert(snd_pcm_hw_params_any(pcm,hw)==0);
 assert(snd_pcm_hw_params_set_access(pcm,hw,SND_PCM_ACCESS_RW_INTERLEAVED)==0);
 assert(snd_pcm_hw_params_set_format(pcm,hw,SND_PCM_FORMAT_S16_LE)==0);
 assert(snd_pcm_hw_params_set_channels(pcm,hw,2)==0);
 assert(snd_pcm_hw_params_set_rate(pcm,hw,44100,0)==0);
 assert(snd_pcm_hw_params_set_period_size(pcm,hw,128,0)==0);
 assert(snd_pcm_hw_params_set_buffer_size(pcm,hw,512)==0);
 assert(snd_pcm_hw_params(pcm,hw)==0);
 assert(snd_pcm_sw_params_current(pcm,sw)==0);
 assert(snd_pcm_sw_params_set_start_threshold(pcm,sw,128+output)==0);
 assert(snd_pcm_sw_params_set_stop_threshold(pcm,sw,512)==0);
 assert(snd_pcm_sw_params_set_silence_threshold(pcm,sw,32)==0);
 assert(snd_pcm_sw_params_set_silence_size(pcm,sw,64)==0);
 assert(snd_pcm_sw_params(pcm,sw)==0);
 snd_pcm_hw_params_free(hw);snd_pcm_sw_params_free(sw);return pcm;
}
static void compare(struct settings a,struct settings b){
 assert(a.rate==b.rate&&a.channels==b.channels&&a.format==b.format&&a.access==b.access);
 assert(a.period==b.period&&a.buffer==b.buffer&&a.start==b.start&&a.stop==b.stop);
 assert(a.silence_threshold==b.silence_threshold&&a.silence_size==b.silence_size);
}
static int (*real_sw)(snd_pcm_t *,snd_pcm_sw_params_t *);
static int sw_count;
static int fail_second_sw(snd_pcm_t *pcm,snd_pcm_sw_params_t *sw){
 if(++sw_count==2)return -EINVAL;
 return real_sw(pcm,sw);
}
int main(void){
 struct rx3_alsa_driver d;assert(rx3_alsa_driver_init(&d)==0);
 snd_pcm_t *pcm[2]={configured(0),configured(1)};
 struct settings expected[2]={inspect(pcm[0]),inspect(pcm[1])};
 for(int i=0;i<2;i++)assert(rx3_alsa_save(&d,i,pcm[i],"null",0)==0);
 /* Snapshot failure must leave the last good settings available. */
 snd_pcm_t *unconfigured;assert(snd_pcm_open(&unconfigured,"null",SND_PCM_STREAM_PLAYBACK,0)==0);
 assert(rx3_alsa_save(&d,0,unconfigured,"null",0)<0);snd_pcm_close(unconfigured);
 struct rx3_audio_pair pair={0};
 assert(rx3_audio_pair_init(&pair,rx3_alsa_pair_driver(&d),pcm[0],pcm[1])==0);
 short samples[256]={0};
 for(int cycle=0;cycle<3;cycle++){
  rx3_audio_pair_lost(&pair,cycle*1000,-ENODEV);
  assert(rx3_audio_pair_retry(&pair,cycle*1000));
  for(int i=0;i<2;i++){
   compare(expected[i],inspect(pair.pcm[i]));
   assert(snd_pcm_prepare(pair.pcm[i])==0);
   assert(snd_pcm_writei(pair.pcm[i],samples,128)==128);
  }
 }
 /* Fail cue software setup after both real PCMs have opened and master is
  * fully configured. Neither handle may survive or become publicly usable. */
 real_sw=d.sw_real;d.sw_real=fail_second_sw;
 rx3_audio_pair_lost(&pair,3000,-ENODEV);
 assert(!rx3_audio_pair_retry(&pair,3000));
 assert(pair.state==RX3_AUDIO_OFFLINE&&pair.last_error==-EINVAL);
 assert(!pair.pcm[0]&&!pair.pcm[1]);
 d.sw_real=real_sw;
 assert(!rx3_audio_pair_retry(&pair,3999));
 assert(rx3_audio_pair_retry(&pair,4000));
 for(int i=0;i<2;i++){
  compare(expected[i],inspect(pair.pcm[i]));
  assert(snd_pcm_prepare(pair.pcm[i])==0);
  assert(snd_pcm_writei(pair.pcm[i],samples,128)==128);
 }
 rx3_audio_pair_stop(&pair);rx3_alsa_driver_destroy(&d);
 puts("PASS real ALSA null: 4 pair reopens preserve settings/audio writes; partial software failure rolls back and recovers");
}
