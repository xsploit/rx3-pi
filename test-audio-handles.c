#include "audio-handles.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
struct pcm {int live;};
struct fake {struct pcm storage[16];int count,closes;};
static int open_pcm(void *ctx,int output,void **pcm){
 struct fake*f=ctx;(void)output;assert(f->count<16);
 f->storage[f->count].live=1;*pcm=&f->storage[f->count++];return 0;
}
static void close_pcm(void *ctx,void *pcm){struct fake*f=ctx;struct pcm*p=pcm;assert(p->live);p->live=0;f->closes++;}
int main(void){
 struct fake f={0};struct rx3_audio_handles h={0};struct rx3_audio_pair pair={0};
 void *initial[2],*token[2],*real,*unpaired;int output;
 for(int i=0;i<2;i++){
  assert(!open_pcm(&f,i,&initial[i]));
  assert(!rx3_audio_handle_open(&h,i,initial[i],&token[i]));assert(token[i]!=initial[i]);
  assert(rx3_audio_handle_resolve(&h,token[i],&real,&output)==RX3_HANDLE_READY);
  assert(real==initial[i]&&output==i);
 }
 assert(rx3_audio_handle_open(&h,0,initial[0],&real)==-EBUSY);
 assert(!rx3_audio_pair_init(&pair,(struct rx3_audio_driver){&f,open_pcm,close_pcm},initial[0],initial[1]));
 assert(!rx3_audio_handles_bind(&h,&pair));
 for(int cycle=0;cycle<3;cycle++){
  rx3_audio_pair_lost(&pair,cycle*1000,-ENODEV);
  for(int i=0;i<2;i++){
   assert(rx3_audio_handle_resolve(&h,token[i],&real,&output)==RX3_HANDLE_UNAVAILABLE);
   assert(!real&&output==i);
  }
  assert(rx3_audio_pair_retry(&pair,cycle*1000));
  for(int i=0;i<2;i++){
   assert(rx3_audio_handle_resolve(&h,token[i],&real,&output)==RX3_HANDLE_READY);
   assert(real==pair.pcm[i]&&real!=initial[i]&&output==i);
  }
 }
 /* A freed old PCM address is not a public token. If ALSA reuses it for
  * unrelated capture, its calls must pass through rather than be redirected. */
 assert(rx3_audio_handle_resolve(&h,initial[0],&real,&output)==RX3_HANDLE_UNMANAGED);
 assert(!real&&output==-1);
 assert(rx3_audio_handle_close(&h,token[0],&unpaired)==1&&!unpaired);
 int closes=f.closes;
 assert(rx3_audio_handle_resolve(&h,token[0],&real,0)==RX3_HANDLE_CLOSED);
 assert(rx3_audio_handle_resolve(&h,token[1],&real,0)==RX3_HANDLE_UNAVAILABLE);
 assert(rx3_audio_handle_close(&h,token[0],&unpaired)==-EBADFD);
 assert(rx3_audio_handle_open(&h,0,initial[0],&real)==-EBUSY);
 assert(rx3_audio_handle_close(&h,token[1],&unpaired)==1&&!unpaired&&f.closes==closes);
 assert(!h.pair);assert(!rx3_audio_handle_close(&h,initial[0],&unpaired));
 /* Discovery can open/configure/close one output before the pair exists. */
 assert(!open_pcm(&f,0,&real));void *probe=real;
 assert(!rx3_audio_handle_open(&h,0,probe,&token[0]));
 assert(rx3_audio_handles_bind(&h,&pair)==-EINVAL);
 assert(rx3_audio_handle_close(&h,token[0],&unpaired)==1&&unpaired==probe);
 close_pcm(&f,unpaired);
 for(int i=0;i<f.count;i++)assert(!f.storage[i].live);
 puts("PASS stable audio handles: replacements, offline lookup, unrelated PCM addresses, pair close and discovery");
}
