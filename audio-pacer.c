#include "audio-pacer.h"
#include <errno.h>
int rx3_audio_pacer_init(struct rx3_audio_pacer *p,unsigned rate,unsigned frames){
 if(!p||!rate||!frames)return -EINVAL;
 *p=(struct rx3_audio_pacer){.rate=rate,.frames=frames};return 0;
}
uint64_t rx3_audio_pacer_deadline(struct rx3_audio_pacer *p,int output,uint64_t now){
 if(output<0||output>1||!p->rate||!p->frames)return 0;
 unsigned bit=1u<<output;
 if(!p->started||p->seen==3||(p->seen&bit)){
  uint64_t numerator=(uint64_t)p->frames*1000000000+p->remainder;
  uint64_t step=numerator/p->rate;
  p->remainder=numerator%p->rate;
  /* Tolerate ordinary scheduler jitter without slowing the engine clock.
   * Discard a long backlog rather than running seconds of callbacks at once. */
  uint64_t limit=step>100000000?step:100000000;
  if(!p->started||(now>p->deadline_ns&&now-p->deadline_ns>limit))p->deadline_ns=now;
  p->deadline_ns+=step;p->seen=bit;p->started=1;
 }else p->seen|=bit;
 return p->deadline_ns;
}
