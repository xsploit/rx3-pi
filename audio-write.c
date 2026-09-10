#include "audio-write.h"
#include <errno.h>
static struct rx3_audio_write_result retry(int error){
 return (struct rx3_audio_write_result){RX3_AUDIO_RETRY,0,error};
}
static struct rx3_audio_write_result lost(struct rx3_audio_pair *p,uint64_t now,int error){
 rx3_audio_pair_lost(p,now,error);
 return (struct rx3_audio_write_result){RX3_AUDIO_UNAVAILABLE,0,error};
}
struct rx3_audio_write_result rx3_audio_write(struct rx3_audio_pair *p,
 const struct rx3_audio_writer *w,int output,const void *samples,
 unsigned long frames,uint64_t now_ms){
 if(output<0||output>1||!w||!w->write||!w->prepare||(!samples&&frames))
  return (struct rx3_audio_write_result){RX3_AUDIO_CLOSED,0,-EINVAL};
 if(p->state==RX3_AUDIO_STOPPED)
  return (struct rx3_audio_write_result){RX3_AUDIO_CLOSED,0,-EBADFD};
 if(!rx3_audio_pair_retry(p,now_ms))
  return (struct rx3_audio_write_result){RX3_AUDIO_UNAVAILABLE,0,p->last_error};
 if(!frames)return (struct rx3_audio_write_result){RX3_AUDIO_PROGRESS,0,0};
 void *pcm=p->pcm[output];
 for(int attempt=0;attempt<2;attempt++){
  long n=w->write(w->context,pcm,samples,frames);
  if(n>0&&((unsigned long)n)<=frames)
   return (struct rx3_audio_write_result){RX3_AUDIO_PROGRESS,n,0};
  if(n==0||n==-EAGAIN)return retry(-EAGAIN);
  if(n>0)return lost(p,now_ms,-EIO); /* Invalid driver result. */
  if(n==-EINTR){if(attempt==0)continue;return retry(-EINTR);}
  if(n!=-EPIPE&&n!=-ESTRPIPE)return lost(p,now_ms,(int)n);
  /* Repeated xrun/suspend after one recovery needs another paced call. */
  if(attempt)return retry((int)n);
  int result;
  if(n==-ESTRPIPE&&w->resume){
   result=w->resume(w->context,pcm);
   if(result==-EAGAIN)return retry(-EAGAIN);
   if(result==-ENODEV)return lost(p,now_ms,result);
   if(result>=0)continue;
  }
  result=w->prepare(w->context,pcm);
  if(result==-EAGAIN||result==-EINTR)return retry(result);
  if(result<0)return lost(p,now_ms,result);
 }
 return retry(-EAGAIN);
}
