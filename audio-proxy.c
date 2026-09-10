#define _GNU_SOURCE
#include "audio-alsa.h"
#include "audio-handles.h"
#include "audio-write.h"
#include "audio-pacer.h"
#include <pthread.h>
#include <dlfcn.h>
#include <errno.h>
#include <string.h>
#include <time.h>
#include <stdio.h>
/* Interposed ALSA recovery for the native RX3 player. */
static pthread_mutex_t mutex=PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
static struct rx3_alsa_driver alsa;
static struct rx3_audio_pair pair;
static struct rx3_audio_handles handles;
static struct rx3_audio_pacer pacer;
static int initialized,ready[2],modes[2],pacing,last_status;
static const char *names[2]={"rx3out","rx3cue"};
static unsigned rate=44100;
static struct {snd_pcm_t *a,*b;} links[16];
static unsigned link_count;
static void *pending_master;
#ifdef RX3_AUDIO_PROXY_TEST
static int test_reopen_error;
#endif
static long (*write_real)(snd_pcm_t*,const void*,unsigned long);
static int (*prepare_real)(snd_pcm_t*),(*resume_real)(snd_pcm_t*);
static int (*wait_real)(snd_pcm_t*,int),(*nonblock_real)(snd_pcm_t*,int);
static int (*link_real)(snd_pcm_t*,snd_pcm_t*);
static uint64_t now_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static int init(void){
 if(initialized)return initialized>0?0:-ENOSYS;
 if(rx3_alsa_driver_init(&alsa)<0){initialized=-1;return -ENOSYS;}
 write_real=dlsym(RTLD_NEXT,"snd_pcm_writei");prepare_real=dlsym(RTLD_NEXT,"snd_pcm_prepare");
 resume_real=dlsym(RTLD_NEXT,"snd_pcm_resume");wait_real=dlsym(RTLD_NEXT,"snd_pcm_wait");
 nonblock_real=dlsym(RTLD_NEXT,"snd_pcm_nonblock");link_real=dlsym(RTLD_NEXT,"snd_pcm_link");
 initialized=write_real&&prepare_real&&resume_real&&wait_real&&nonblock_real&&link_real?1:-1;
 return initialized>0?0:-ENOSYS;
}
static int map_pcm(snd_pcm_t **pcm,int *output){
 void *real;enum rx3_audio_handle_state state=rx3_audio_handle_resolve(&handles,*pcm,&real,output);
 if(state==RX3_HANDLE_UNMANAGED)return 0;
 if(state==RX3_HANDLE_READY){*pcm=real;return 0;}
 return state==RX3_HANDLE_CLOSED?-EBADFD:-ENODEV;
}
static snd_pcm_t *link_target(snd_pcm_t *token,void **next){
 void *unused;int output;enum rx3_audio_handle_state state=rx3_audio_handle_resolve(&handles,token,&unused,&output);
 if(state==RX3_HANDLE_UNMANAGED)return token;
 if(state==RX3_HANDLE_CLOSED)return 0;
 return next[output];
}
static int reopen(void *ctx,int output,void **handle){
 (void)ctx;
#ifdef RX3_AUDIO_PROXY_TEST
 if(test_reopen_error){*handle=0;return test_reopen_error;}
#endif
 struct rx3_audio_driver base=rx3_alsa_pair_driver(&alsa);
 if(output==0)pending_master=0;
 int result=base.open_configured(base.context,output,handle);if(result<0)return result;
 if(output==0){pending_master=*handle;return 0;}
 void *next[2]={pending_master,*handle};
 for(unsigned i=0;i<link_count;i++){
  snd_pcm_t *a=link_target(links[i].a,next),*b=link_target(links[i].b,next);
  if(!a||!b)return -EBADFD;
  if((result=link_real(a,b))<0)return result;
 }
 return 0;
}
static void close_real(void *ctx,void *pcm){(void)ctx;alsa.close_real(pcm);}
static int bind_if_ready(void){
 if(handles.pair||!ready[0]||!ready[1])return 0;
 int result=rx3_audio_pair_init(&pair,(struct rx3_audio_driver){0,reopen,close_real},handles.slot[0].initial,handles.slot[1].initial);
 if(result<0)return result;
 if((result=rx3_audio_handles_bind(&handles,&pair))<0)return result;
 snd_pcm_hw_params_get_rate(alsa.saved[0].hw,&rate,0);pacing=0;return 0;
}
int snd_pcm_open(snd_pcm_t **pcm,const char *name,snd_pcm_stream_t stream,int mode){
 pthread_mutex_lock(&mutex);int result=init();if(result<0)goto done;
 const char *target=name;int output=-1;
 if(!strcmp(name,"rx3out"))output=0;
 else if(!strcmp(name,"rx3cue"))output=1;
 else if(!strncmp(name,"hw:cs4344audiorev8,",sizeof("hw:cs4344audiorev8,")-1)||!strncmp(name,"hw:esaics4344audio,",sizeof("hw:esaics4344audio,")-1)){
  unsigned n=strlen(name);output=stream==SND_PCM_STREAM_PLAYBACK&&n&&name[n-1]=='0'?0:(stream==SND_PCM_STREAM_PLAYBACK&&n&&name[n-1]=='1'?1:-1);
  target=output>=0?names[output]:"null";
 }
 if(stream!=SND_PCM_STREAM_PLAYBACK)output=-1;
 if(output<0){result=alsa.open_real(pcm,target,stream,mode);goto done;}
 if(handles.pair||handles.slot[output].active){result=-EBUSY;goto done;}
 snd_pcm_t *real=0;result=alsa.open_real(&real,target,stream,mode);
 if(result<0)goto done;
 void *token=0;result=rx3_audio_handle_open(&handles,output,real,&token);
 if(result<0){alsa.close_real(real);goto done;}
 *pcm=token;ready[output]=0;modes[output]=mode;
done:
 pthread_mutex_unlock(&mutex);return result;
}
/* Hold the recursive lock through ALSA so native close cannot race a write.
 * Recursive entry is required for ALSA's internal calls with real handles. */
#define ROUTE() int output=-1;int error=map_pcm(&pcm,&output);if(error){pthread_mutex_unlock(&mutex);return error;}
#define WRAP_LOOKUP(type,name,decl,args,lookup) type name decl {pthread_mutex_lock(&mutex);static __typeof__(&name) real;if(!real)real=lookup;if(!real){pthread_mutex_unlock(&mutex);return -ENOSYS;}ROUTE();type result=real args;pthread_mutex_unlock(&mutex);return result;}
#define WRAP(type,name,decl,args) WRAP_LOOKUP(type,name,decl,args,dlsym(RTLD_NEXT,#name))
/* The embedded ALSA exports both the old value ABI and rc4 pointer ABI.
 * dlsym alone can select the old implementation even for a versioned wrapper. */
#define WRAP_RC4(type,name,decl,args) WRAP_LOOKUP(type,name,decl,args,dlvsym(RTLD_NEXT,#name,"ALSA_0.9.0rc4"))
WRAP(int,snd_pcm_hw_params_any,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p),(pcm,p))
WRAP(int,snd_pcm_hw_params_current,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p),(pcm,p))
WRAP(int,snd_pcm_hw_params,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p),(pcm,p))
WRAP(int,snd_pcm_hw_params_set_format,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,snd_pcm_format_t v),(pcm,p,v))
WRAP(int,snd_pcm_hw_params_set_channels,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,unsigned v),(pcm,p,v))
WRAP(int,snd_pcm_hw_params_set_rate,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,unsigned v,int dir),(pcm,p,v,dir))
WRAP_RC4(int,snd_pcm_hw_params_set_rate_near,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,unsigned *v,int *dir),(pcm,p,v,dir))
WRAP(int,snd_pcm_hw_params_test_rate,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,unsigned v,int dir),(pcm,p,v,dir))
WRAP(int,snd_pcm_hw_params_set_period_size,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,snd_pcm_uframes_t v,int dir),(pcm,p,v,dir))
WRAP(int,snd_pcm_hw_params_set_buffer_size,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,snd_pcm_uframes_t v),(pcm,p,v))
WRAP_RC4(int,snd_pcm_hw_params_set_period_size_near,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,snd_pcm_uframes_t *v,int *dir),(pcm,p,v,dir))
WRAP_RC4(int,snd_pcm_hw_params_set_periods_near,(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,unsigned *v,int *dir),(pcm,p,v,dir))
WRAP(int,snd_pcm_sw_params_current,(snd_pcm_t *pcm,snd_pcm_sw_params_t *p),(pcm,p))
WRAP(int,snd_pcm_sw_params_set_start_threshold,(snd_pcm_t *pcm,snd_pcm_sw_params_t *p,snd_pcm_uframes_t v),(pcm,p,v))
WRAP(int,snd_pcm_sw_params_set_stop_threshold,(snd_pcm_t *pcm,snd_pcm_sw_params_t *p,snd_pcm_uframes_t v),(pcm,p,v))
WRAP(int,snd_pcm_sw_params_set_silence_threshold,(snd_pcm_t *pcm,snd_pcm_sw_params_t *p,snd_pcm_uframes_t v),(pcm,p,v))
WRAP(int,snd_pcm_sw_params_set_silence_size,(snd_pcm_t *pcm,snd_pcm_sw_params_t *p,snd_pcm_uframes_t v),(pcm,p,v))
WRAP(int,snd_pcm_prepare,(snd_pcm_t *pcm),(pcm))
WRAP(int,snd_pcm_nonblock,(snd_pcm_t *pcm,int v),(pcm,v))
WRAP(snd_pcm_sframes_t,snd_pcm_readi,(snd_pcm_t *pcm,void *p,snd_pcm_uframes_t n),(pcm,p,n))
int snd_pcm_hw_params_set_access(snd_pcm_t *pcm,snd_pcm_hw_params_t *p,snd_pcm_access_t v){
 pthread_mutex_lock(&mutex);static __typeof__(&snd_pcm_hw_params_set_access) real;if(!real)real=dlsym(RTLD_NEXT,"snd_pcm_hw_params_set_access");ROUTE();
 int result=real(pcm,p,v==SND_PCM_ACCESS_RW_NONINTERLEAVED?SND_PCM_ACCESS_RW_INTERLEAVED:v);pthread_mutex_unlock(&mutex);return result;
}
int snd_pcm_sw_params(snd_pcm_t *pcm,snd_pcm_sw_params_t *p){
 pthread_mutex_lock(&mutex);ROUTE();static __typeof__(&snd_pcm_sw_params) real;if(!real)real=dlsym(RTLD_NEXT,"snd_pcm_sw_params");
 int result=real(pcm,p);
 if(result>=0&&output>=0){
  result=rx3_alsa_save(&alsa,output,pcm,names[output],modes[output]);
  if(result>=0){ready[output]=1;result=bind_if_ready();}
 }
 pthread_mutex_unlock(&mutex);return result;
}
int snd_pcm_link(snd_pcm_t *a,snd_pcm_t *b){
 pthread_mutex_lock(&mutex);int result=init(),ia=-1,ib=-1;snd_pcm_t *real_a=a,*real_b=b;
 if(result>=0)result=map_pcm(&real_a,&ia);
 if(result>=0)result=map_pcm(&real_b,&ib);
 int tracked=ia>=0||ib>=0,exists=0;
 for(unsigned i=0;i<link_count;i++)if(links[i].a==a&&links[i].b==b)exists=1;
 if(result>=0&&tracked&&!exists&&link_count==16)result=-ENOSPC;
 if(result>=0)result=link_real(real_a,real_b);
 if(result>=0&&tracked&&!exists){links[link_count].a=a;links[link_count++].b=b;}
 pthread_mutex_unlock(&mutex);return result;
}
int snd_pcm_close(snd_pcm_t *pcm){
 pthread_mutex_lock(&mutex);int result=init();if(result<0){pthread_mutex_unlock(&mutex);return result;}
 void *unpaired=0;int output=-1;void *ignored;
 enum rx3_audio_handle_state state=rx3_audio_handle_resolve(&handles,pcm,&ignored,&output);
 if(output>=0){link_count=0;ready[output]=0;}
 else for(unsigned i=0;i<link_count;)if(links[i].a==pcm||links[i].b==pcm)links[i]=links[--link_count];else i++;
 result=rx3_audio_handle_close(&handles,pcm,&unpaired);
 if(result==0)result=alsa.close_real(pcm);
 else if(result>0)result=unpaired?alsa.close_real(unpaired):0;
 if(state!=RX3_HANDLE_UNMANAGED&&!handles.slot[0].active&&!handles.slot[1].active){rx3_alsa_driver_destroy(&alsa);ready[0]=ready[1]=0;pacing=0;}
 pthread_mutex_unlock(&mutex);return result;
}
static long bounded_write(void *ctx,void *pcm,const void *samples,unsigned long frames){
 (void)ctx;int result=nonblock_real(pcm,1);if(result<0)return result;
 long n=write_real(pcm,samples,frames);
 if(n!=-EAGAIN)return n;
 result=wait_real(pcm,20);if(result<0)return result;if(!result)return -EAGAIN;
 return write_real(pcm,samples,frames);
}
static int prepare(void *ctx,void *pcm){(void)ctx;return prepare_real(pcm);}
static int resume(void *ctx,void *pcm){(void)ctx;return resume_real(pcm);}
snd_pcm_sframes_t snd_pcm_writei(snd_pcm_t *pcm,const void *samples,snd_pcm_uframes_t frames){
 pthread_mutex_lock(&mutex);int result=init(),output=-1;void *current;
 if(result<0){pthread_mutex_unlock(&mutex);return result;}
 enum rx3_audio_handle_state state=rx3_audio_handle_resolve(&handles,pcm,&current,&output);
 if(state==RX3_HANDLE_UNMANAGED||(!handles.pair&&state==RX3_HANDLE_READY)){
  long n=write_real(state==RX3_HANDLE_UNMANAGED?pcm:current,samples,frames);pthread_mutex_unlock(&mutex);return n;
 }
 if(state==RX3_HANDLE_CLOSED){pthread_mutex_unlock(&mutex);return -EBADFD;}
 struct rx3_audio_writer writer={0,bounded_write,prepare,resume};
 struct rx3_audio_write_result r=rx3_audio_write(&pair,&writer,output,samples,frames,now_ns()/1000000);
 if(r.state==RX3_AUDIO_PROGRESS){
  if(last_status)fprintf(stderr,"RX3 audio output restored\n");
  last_status=0;pacing=0;
  pthread_mutex_unlock(&mutex);return r.frames;
 }
 if(last_status!=(int)r.state+1){fprintf(stderr,"RX3 audio unavailable/retry: %d\n",r.error);last_status=(int)r.state+1;}
 uint64_t deadline=0;
 if(r.state!=RX3_AUDIO_CLOSED&&frames){
  if(!pacing||pacer.frames!=frames){rx3_audio_pacer_init(&pacer,rate,(unsigned)frames);pacing=1;}
  deadline=rx3_audio_pacer_deadline(&pacer,output,now_ns());
 }
 pthread_mutex_unlock(&mutex);
 if(deadline>now_ns()){
  struct timespec t={(time_t)(deadline/1000000000),(long)(deadline%1000000000)};
  while(clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&t,0)==EINTR){}
 }
 /* RX3 treats EPIPE as a skipped block. Do not return fabricated frame counts
  * or forward device loss to its vendor /dev/mem error-recovery branch. */
 return -EPIPE;
}
#ifdef RX3_AUDIO_PROXY_TEST
void rx3_audio_proxy_test_absent(int absent){pthread_mutex_lock(&mutex);test_reopen_error=absent?-ENODEV:0;pthread_mutex_unlock(&mutex);}
void rx3_audio_proxy_test_loss(void){pthread_mutex_lock(&mutex);rx3_audio_pair_lost(&pair,now_ns()/1000000,-ENODEV);pthread_mutex_unlock(&mutex);}
#endif
