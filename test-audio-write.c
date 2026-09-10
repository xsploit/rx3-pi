#include "audio-write.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
struct pcm {int live,output;};
struct fake {
 struct pcm handles[32];int used,opens,closes,absent;
 long results[4];int at,writes,prepares,resumes,prepare_result,resume_result;
 void *last_written;
};
static int open_pcm(void *ctx,int output,void **p){
 struct fake*f=ctx;f->opens++;if(f->absent)return -ENODEV;
 assert(f->used<32);struct pcm*h=&f->handles[f->used++];
 *h=(struct pcm){1,output};*p=h;return 0;
}
static void close_pcm(void *ctx,void *p){struct fake*f=ctx;struct pcm*h=p;assert(h->live);h->live=0;f->closes++;}
static long write_pcm(void *ctx,void *p,const void *samples,unsigned long frames){
 struct fake*f=ctx;assert(((struct pcm*)p)->live&&samples&&frames==128);
 f->last_written=p;f->writes++;assert(f->at<4);return f->results[f->at++];
}
static int prepare(void *ctx,void *p){struct fake*f=ctx;assert(((struct pcm*)p)->live);f->prepares++;return f->prepare_result;}
static int resume(void *ctx,void *p){struct fake*f=ctx;assert(((struct pcm*)p)->live);f->resumes++;return f->resume_result;}
static void scenario(struct fake*f,long first,long second){
 f->results[0]=first;f->results[1]=second;f->at=f->writes=f->prepares=f->resumes=0;
 f->prepare_result=f->resume_result=0;
}
int main(void){
 struct fake f={0};void*a,*b;assert(!open_pcm(&f,0,&a)&&!open_pcm(&f,1,&b));
 struct rx3_audio_pair p={0};assert(!rx3_audio_pair_init(&p,(struct rx3_audio_driver){&f,open_pcm,close_pcm},a,b));
 struct rx3_audio_writer w={&f,write_pcm,prepare,resume};short samples[256]={0};
#define WRITE(d,t) rx3_audio_write(&p,&w,d,samples,128,t)
 struct rx3_audio_write_result r;
 scenario(&f,64,0);r=WRITE(0,0);assert(r.state==RX3_AUDIO_PROGRESS&&r.frames==64&&f.writes==1);
 scenario(&f,-EPIPE,128);r=WRITE(0,0);assert(r.frames==128&&f.prepares==1&&f.writes==2&&f.closes==0);
 scenario(&f,-EPIPE,-EPIPE);r=WRITE(0,0);assert(r.state==RX3_AUDIO_RETRY&&r.frames==0&&f.prepares==1&&f.writes==2);
 scenario(&f,-EINTR,-EINTR);r=WRITE(0,0);assert(r.state==RX3_AUDIO_RETRY&&f.writes==2&&!f.prepares);
 scenario(&f,-EAGAIN,128);r=WRITE(1,0);assert(r.state==RX3_AUDIO_RETRY&&f.writes==1);
 scenario(&f,-ESTRPIPE,128);f.resume_result=-EAGAIN;
 r=WRITE(1,0);assert(r.state==RX3_AUDIO_RETRY&&f.resumes==1&&f.writes==1&&!f.prepares);
 scenario(&f,-ESTRPIPE,128);r=WRITE(1,0);assert(r.frames==128&&f.resumes==1&&!f.prepares);
 scenario(&f,-ESTRPIPE,128);f.resume_result=-ENOSYS;
 r=WRITE(1,0);assert(r.frames==128&&f.resumes==1&&f.prepares==1);
 scenario(&f,-EPIPE,128);f.prepare_result=-ENODEV;
 r=WRITE(0,100);assert(r.state==RX3_AUDIO_UNAVAILABLE&&r.frames==0&&f.closes==2);
 f.absent=1;int opens=f.opens,writes=f.writes;
 r=WRITE(1,100);assert(r.state==RX3_AUDIO_UNAVAILABLE&&f.opens==opens+1&&f.writes==writes);
 r=WRITE(0,1099);assert(r.state==RX3_AUDIO_UNAVAILABLE&&f.opens==opens+1);
 f.absent=0;scenario(&f,128,0);r=WRITE(1,1100);
 assert(r.frames==128&&f.last_written==p.pcm[1]&&p.pcm[0]!=a&&p.pcm[1]!=b);
 scenario(&f,-ENODEV,0);r=WRITE(1,1200);assert(r.state==RX3_AUDIO_UNAVAILABLE&&f.closes==4);
 scenario(&f,128,0);r=WRITE(0,1200);assert(r.frames==128&&f.last_written==p.pcm[0]);
 rx3_audio_pair_stop(&p);opens=f.opens;writes=f.writes;
 r=WRITE(0,9999);assert(r.state==RX3_AUDIO_CLOSED&&r.frames==0&&f.opens==opens&&f.writes==writes);
 for(int i=0;i<f.used;i++)assert(!f.handles[i].live);
 puts("PASS bounded audio writes: partial writes, xrun, suspend, interruptions, pair loss/reopen and stop");
}
