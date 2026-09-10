#include "audio-alsa.h"
#include "audio-handles.h"
#include <dlfcn.h>
#include <time.h>
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
static snd_pcm_t *configured(int output, const char *name){
 snd_pcm_t *pcm;assert(snd_pcm_open(&pcm,name,SND_PCM_STREAM_PLAYBACK,0)==0);
 snd_pcm_hw_params_t *hw;snd_pcm_sw_params_t *sw;
 assert(snd_pcm_hw_params_malloc(&hw)==0&&snd_pcm_sw_params_malloc(&sw)==0);
 assert(snd_pcm_hw_params_any(pcm,hw)==0);
 assert(snd_pcm_hw_params_set_access(pcm,hw,SND_PCM_ACCESS_RW_INTERLEAVED)==0);
 assert(snd_pcm_hw_params_set_format(pcm,hw,SND_PCM_FORMAT_S16_LE)==0);
 assert(snd_pcm_hw_params_set_channels(pcm,hw,2)==0);
 unsigned rate=44100,periods=4;int direction=0;snd_pcm_uframes_t period=128;
 assert(snd_pcm_hw_params_test_rate(pcm,hw,rate,0)==0);
 assert(snd_pcm_hw_params_set_rate_near(pcm,hw,&rate,&direction)==0&&rate==44100);
 assert(snd_pcm_hw_params_set_periods_near(pcm,hw,&periods,&direction)==0&&periods==4);
 assert(snd_pcm_hw_params_set_period_size_near(pcm,hw,&period,&direction)==0&&period==128);
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
int main(void){
 void (*loss)(void)=dlsym(RTLD_DEFAULT,"rx3_audio_proxy_test_loss");assert(loss);
 void (*absent)(int)=dlsym(RTLD_DEFAULT,"rx3_audio_proxy_test_absent");assert(absent);
 short samples[256]={0};
 const char *names[2]={"hw:cs4344audiorev8,0","hw:esaics4344audio,1"};
 for(int order=0;order<2;order++){
  snd_pcm_t *pcm[2]={configured(0,names[0]),configured(1,names[1])};
  struct settings expected[2]={inspect(pcm[0]),inspect(pcm[1])};
  snd_pcm_t *other;
  assert(snd_pcm_open(&other,"null",SND_PCM_STREAM_CAPTURE,0)==0);
  /* null PCMs cannot link: routing both tokens must safely return an error. */
  assert(snd_pcm_link(pcm[0],pcm[1])<0);
  assert(snd_pcm_link(pcm[0],other)<0);
  assert(snd_pcm_close(other)==0);
  for(int cycle=0;cycle<4;cycle++){
   loss();
   assert(snd_pcm_prepare(pcm[0])==-ENODEV);
   for(int j=0;j<2;j++){
    int i=j^order;
    assert(snd_pcm_writei(pcm[i],samples,128)==128);
    compare(expected[i],inspect(pcm[i]));
    assert(snd_pcm_prepare(pcm[i])==0);
   }
  }
  absent(1);loss();
  struct timespec begin,end;clock_gettime(CLOCK_MONOTONIC,&begin);
  for(int block=0;block<32;block++)for(int i=0;i<2;i++)
   assert(snd_pcm_writei(pcm[i],samples,128)==-EPIPE);
  clock_gettime(CLOCK_MONOTONIC,&end);
  double ms=(end.tv_sec-begin.tv_sec)*1000.0+(end.tv_nsec-begin.tv_nsec)/1000000.0;
  assert(ms>=92.0&&ms<350.0);
  absent(0);
  struct timespec delay={1,10000000};nanosleep(&delay,0);
  for(int i=0;i<2;i++)assert(snd_pcm_writei(pcm[i],samples,128)==128);
  printf("Offline 32 paired blocks: %.3f ms (expected 92.880)\n",ms);
  assert(snd_pcm_close(pcm[order])==0);
  assert(snd_pcm_writei(pcm[order],samples,128)==-EBADFD);
  assert(snd_pcm_prepare(pcm[1-order])==-ENODEV);
  assert(snd_pcm_close(pcm[1-order])==0);
  assert(snd_pcm_close(pcm[order])==-EBADFD);
 }
 puts("PASS interposed ALSA: vendor aliases, 8 pair reopens using unchanged public handles, settings, writes, capture passthrough, rejected links, both close orders");
 return 0;
}
#ifdef RX3_TEST_PRELOAD
__attribute__((constructor))static void run_preloaded_test(void){exit(main());}
#endif
