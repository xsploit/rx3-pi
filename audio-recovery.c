#include "audio-recovery.h"
#include <errno.h>
static void close_pair(struct rx3_audio_pair *p,void **handles){
 for(int i=0;i<2;i++)if(handles[i]){
  void *h=handles[i];handles[i]=0;p->driver.close(p->driver.context,h);
 }
}
int rx3_audio_pair_init(struct rx3_audio_pair *p,struct rx3_audio_driver driver,void *master,void *cue){
 if(!p||!driver.open_configured||!driver.close||!master||!cue||master==cue)return -EINVAL;
 *p=(struct rx3_audio_pair){.driver=driver,.pcm={master,cue},.state=RX3_AUDIO_LIVE};
 return 0;
}
void rx3_audio_pair_lost(struct rx3_audio_pair *p,uint64_t now_ms,int error){
 if(p->state!=RX3_AUDIO_LIVE)return;
 p->state=RX3_AUDIO_OFFLINE;p->last_error=error;p->next_retry_ms=now_ms;
 close_pair(p,p->pcm);
}
int rx3_audio_pair_retry(struct rx3_audio_pair *p,uint64_t now_ms){
 if(p->state==RX3_AUDIO_LIVE)return 1;
 if(p->state!=RX3_AUDIO_OFFLINE||now_ms<p->next_retry_ms)return 0;
 /* A failed attempt cannot be retried by every subsequent audio callback. */
 p->next_retry_ms=now_ms+1000;
 void *next[2]={0,0};
 for(int i=0;i<2;i++){
  int result=p->driver.open_configured(p->driver.context,i,&next[i]);
  if(result<0||!next[i]){
   p->last_error=result<0?result:-EIO;close_pair(p,next);return 0;
  }
 }
 p->pcm[0]=next[0];p->pcm[1]=next[1];p->state=RX3_AUDIO_LIVE;p->last_error=0;
 return 1;
}
void rx3_audio_pair_stop(struct rx3_audio_pair *p){
 if(p->state==RX3_AUDIO_STOPPED)return;
 p->state=RX3_AUDIO_STOPPED;close_pair(p,p->pcm);
}
