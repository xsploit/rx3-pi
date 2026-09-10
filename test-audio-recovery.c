#include "audio-recovery.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
struct pcm {int open,configured,card,output;};
struct fake {
 struct rx3_audio_pair *pair;
 struct pcm handles[64];int used,opens,closes;
 int card,absent,fail_output,null_success;
};
static void *allocate(struct fake *f,int output){
 assert(f->used<64);struct pcm *h=&f->handles[f->used++];
 *h=(struct pcm){.open=1,.card=f->card,.output=output};return h;
}
static int open_configured(void *ctx,int output,void **handle){
 struct fake*f=ctx;f->opens++;
 /* Never expose a replacement master while headphone setup is incomplete. */
 assert(f->pair->state==RX3_AUDIO_OFFLINE);
 assert(!f->pair->pcm[0]&&!f->pair->pcm[1]);
 if(f->absent)return -ENODEV;
 if(f->null_success)return 0;
 *handle=allocate(f,output);
 if(f->fail_output==output)return -EINVAL; /* opened, parameter setup failed */
 ((struct pcm*)*handle)->configured=1;return 0;
}
static void close_pcm(void *ctx,void *handle){
 struct fake*f=ctx;struct pcm*h=handle;assert(h->open);h->open=0;f->closes++;
}
static int live_handles(struct fake*f){int n=0;for(int i=0;i<f->used;i++)n+=f->handles[i].open;return n;}
int main(void){
 struct rx3_audio_pair p={0};struct fake f={.pair=&p,.card=2,.fail_output=-1};
 struct rx3_audio_driver driver={&f,open_configured,close_pcm};
 void *master=allocate(&f,0),*cue=allocate(&f,1);
 assert(rx3_audio_pair_init(&p,driver,master,master)==-EINVAL);
 assert(rx3_audio_pair_init(&p,driver,master,cue)==0);
 assert(rx3_audio_pair_retry(&p,0)&&f.opens==0);
 rx3_audio_pair_lost(&p,100,-ENODEV);assert(live_handles(&f)==0&&f.closes==2);
 f.absent=1;assert(!rx3_audio_pair_retry(&p,100));assert(f.opens==1);
 /* A second output reporting the same loss must not reset the retry clock. */
 rx3_audio_pair_lost(&p,101,-ENODEV);
 for(int i=101;i<1100;i++)assert(!rx3_audio_pair_retry(&p,i));
 assert(f.opens==1&&p.last_error==-ENODEV);
 assert(!rx3_audio_pair_retry(&p,1100)&&f.opens==2);
 f.absent=0;f.card=4;f.fail_output=1;
 assert(!rx3_audio_pair_retry(&p,2100));assert(live_handles(&f)==0);
 assert(f.closes==4&&p.last_error==-EINVAL); /* closes configured master + partial cue */
 f.fail_output=0;assert(!rx3_audio_pair_retry(&p,3100));assert(live_handles(&f)==0&&f.closes==5);
 f.fail_output=-1;f.null_success=1;
 assert(!rx3_audio_pair_retry(&p,4100)&&p.last_error==-EIO);
 f.null_success=0;assert(rx3_audio_pair_retry(&p,5100));
 assert(p.state==RX3_AUDIO_LIVE&&live_handles(&f)==2&&p.last_error==0);
 for(int i=0;i<2;i++){
  struct pcm*h=p.pcm[i];assert(h->configured&&h->card==4&&h->output==i);
 }
 rx3_audio_pair_lost(&p,5200,-ENODEV);assert(live_handles(&f)==0);
 rx3_audio_pair_stop(&p);int opens=f.opens,closes=f.closes;
 assert(!rx3_audio_pair_retry(&p,9000));rx3_audio_pair_lost(&p,9001,-ENODEV);
 rx3_audio_pair_stop(&p);assert(opens==f.opens&&closes==f.closes);
 assert(p.state==RX3_AUDIO_STOPPED);
 master=allocate(&f,0);cue=allocate(&f,1);
 assert(rx3_audio_pair_init(&p,driver,master,cue)==0);
 rx3_audio_pair_stop(&p);rx3_audio_pair_stop(&p);assert(live_handles(&f)==0);
 puts("PASS audio pair: absent device/backoff, partial setup rollback, card change, recovery and stop");
}
