#include "audio-handles.h"
#include <errno.h>
static int index_of(const struct rx3_audio_handles *h,const void *token){
 for(int i=0;i<2;i++)if(token==&h->slot[i])return i;
 return -1;
}
int rx3_audio_handle_open(struct rx3_audio_handles *h,int output,void *pcm,void **token){
 if(output<0||output>1||!pcm||!token||index_of(h,pcm)>=0)return -EINVAL;
 if(h->pair||h->slot[output].active)return -EBUSY;
 if(h->slot[1-output].active&&h->slot[1-output].initial==pcm)return -EINVAL;
 h->slot[output].active=1;h->slot[output].initial=pcm;*token=&h->slot[output];return 0;
}
int rx3_audio_handles_bind(struct rx3_audio_handles *h,struct rx3_audio_pair *pair){
 if(h->pair||!pair||pair->state!=RX3_AUDIO_LIVE)return -EINVAL;
 for(int i=0;i<2;i++)if(!h->slot[i].active||h->slot[i].initial!=pair->pcm[i])return -EINVAL;
 h->pair=pair;h->slot[0].initial=h->slot[1].initial=0;return 0;
}
enum rx3_audio_handle_state rx3_audio_handle_resolve(const struct rx3_audio_handles *h,
 const void *token,void **pcm,int *output){
 *pcm=0;if(output)*output=-1;int i=index_of(h,token);
 if(i<0)return RX3_HANDLE_UNMANAGED;
 if(output)*output=i;
 if(!h->slot[i].active)return RX3_HANDLE_CLOSED;
 if(!h->pair){*pcm=h->slot[i].initial;return RX3_HANDLE_READY;}
 if(h->pair->state!=RX3_AUDIO_LIVE)return RX3_HANDLE_UNAVAILABLE;
 *pcm=h->pair->pcm[i];return RX3_HANDLE_READY;
}
int rx3_audio_handle_close(struct rx3_audio_handles *h,const void *token,void **unpaired){
 *unpaired=0;int i=index_of(h,token);if(i<0)return 0;
 if(!h->slot[i].active)return -EBADFD;
 h->slot[i].active=0;
 if(h->pair)rx3_audio_pair_stop(h->pair);
 else {*unpaired=h->slot[i].initial;h->slot[i].initial=0;}
 if(!h->slot[0].active&&!h->slot[1].active)h->pair=0;
 return 1;
}
