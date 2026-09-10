#include "mixer-state.h"
#include <string.h>
const struct rx3_mixer_binding rx3_mixer_bindings[RX3_MIXER_COUNT]={
 {0x5019,1},{0x501a,1},{0x501b,1},{0x501c,1},{0x509d,1},{0x501e,1},
 {0x4403,0},{0x6017,0},{0x4406,0},{0x4405,0},
 {0x5019,2},{0x501a,2},{0x501b,2},{0x501c,2},{0x509d,2},{0x501e,2}
};
/* Multiple input threads are serialized only for this small metadata update. */
static uint32_t guard,sequence,levels[RX3_MIXER_COUNT],valid,cue,held;
static void lock(void){while(__atomic_exchange_n(&guard,1,__ATOMIC_ACQUIRE)){} }
static void unlock(void){__atomic_store_n(&guard,0,__ATOMIC_RELEASE);}
void rx3_mixer_observe(int key,int operation,int channel,float value){
 int index=-1;
 if(operation==4){
  for(int i=0;i<RX3_MIXER_COUNT;i++)if(rx3_mixer_bindings[i].key==key&&rx3_mixer_bindings[i].channel==channel){index=i;break;}
  if(index<0)return;
  uint32_t bits;memcpy(&bits,&value,4);
  if((bits&0x7f800000)==0x7f800000||value<0.f||value>1.f)return;
  lock();levels[index]=bits;valid|=1u<<index;sequence++;unlock();
 }else if(key==0x5020&&(channel==1||channel==2)&&(operation==0||operation==2)){
  uint32_t bit=1u<<(channel-1);lock();
  if(operation==0){if(!(held&bit)){cue^=bit;sequence++;}held|=bit;}else held&=~bit;
  unlock();
 }
}
int rx3_mixer_snapshot(struct rx3_mixer_snapshot *out){
 /* Snapshot under the same short lock: floats are never read while written. */
 lock();memcpy(out->levels,levels,sizeof(levels));out->valid=valid;out->cue=cue;out->revision=sequence;unlock();return 1;
}
void rx3_dispatch_key(void *manager,int key,int operation,int channel,long value,float analog,long extra){
 ((void(*)(void*,int,int,int,long,float,long))0x37ad64)(manager,key,operation,channel,value,analog,extra);
 rx3_mixer_observe(key,operation,channel,analog);
}
