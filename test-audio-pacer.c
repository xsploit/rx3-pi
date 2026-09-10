#include "audio-pacer.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
static void clock_run(unsigned rate,unsigned frames,unsigned blocks){
 struct rx3_audio_pacer p={0};assert(!rx3_audio_pacer_init(&p,rate,frames));
 uint64_t start=123456789,now=start;
 for(unsigned i=0;i<blocks;i++){
  /* Alternate which output arrives first. The second shares its deadline. */
  int first=i%2;uint64_t next=rx3_audio_pacer_deadline(&p,first,now);
  assert(next>now);now=next;
  assert(rx3_audio_pacer_deadline(&p,1-first,now)==now);
 }
 assert(now-start==(uint64_t)blocks*frames*1000000000/rate);
}
int main(void){
 clock_run(44100,128,44100);clock_run(48000,128,48000);clock_run(96000,256,96000);
 struct rx3_audio_pacer p={0};
 assert(rx3_audio_pacer_init(&p,0,128)==-EINVAL);
 assert(!rx3_audio_pacer_deadline(&p,0,100));
 assert(!rx3_audio_pacer_init(&p,44100,128));
 uint64_t now=1000000000;
 for(int i=0;i<1000;i++){
  uint64_t next=rx3_audio_pacer_deadline(&p,1,now);
  assert(next>now&&next-now<=2902495);now=next;
 }
 /* After a long pause, wait one period, not zero until old time catches up. */
 now+=5000000000;
 uint64_t next=rx3_audio_pacer_deadline(&p,1,now);
 assert(next>now&&next-now<=2902495);
 assert(rx3_audio_pacer_deadline(&p,0,now)==next);
 /* Rejoining both outputs must not retain a missing-output frame backlog. */
 now=next;next=rx3_audio_pacer_deadline(&p,0,now);
 assert(next>now);assert(rx3_audio_pacer_deadline(&p,1,next)==next);
 assert(!rx3_audio_pacer_deadline(&p,2,next));
 /* New session/rate starts at the supplied current time. */
 assert(!rx3_audio_pacer_init(&p,48000,480));
 assert(rx3_audio_pacer_deadline(&p,0,9000000000)==9010000000);
 assert(rx3_audio_pacer_deadline(&p,1,9010000000)==9010000000);
 /* Periodic 8ms wakeup jitter must not make a 2.9ms block clock run slow. */
 assert(!rx3_audio_pacer_init(&p,44100,128));now=1000000000;
 for(int i=0;i<24;i++){
  uint64_t deadline=rx3_audio_pacer_deadline(&p,0,now);
  if(now<deadline)now=deadline;
  if(i%3==0)now+=8000000;
  assert(rx3_audio_pacer_deadline(&p,1,now)==deadline);
 }
 assert(p.deadline_ns==1000000000+(uint64_t)24*128*1000000000/44100);
 puts("PASS offline audio pacing: exact fractional periods, shared pair clock, missing output, long pause and reset");
}
