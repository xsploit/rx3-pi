#ifndef RX3_PAD_INTENT_H
#define RX3_PAD_INTENT_H
/* Owned by the FIFO reader thread. Zero means no accepted MIDI press. */
struct pad_intents { unsigned char held[2][8]; };
static int forward_pad_intent(struct pad_intents *s,int key,int op,int ch,int bank,
 void *ctx,int (*select)(void*,int,int),int (*mode)(void*,int),
 void (*emit)(void*,int,int,int)){
 if(key<0x4117||key>0x411e||ch<1||ch>2||bank<0||bank>7)return 0;
 unsigned char *held=&s->held[ch-1][key-0x4117];
 if(op==0){
  if(*held==bank+1)return 0;
  if(!select(ctx,ch-1,bank))return -1;
  *held=bank+1;
 }else if(op==2){
  if(*held!=bank+1)return 0;
  *held=0;
  /* A later native bank change must not turn this into another action's up. */
  if(mode(ctx,ch-1)!=bank)return 0;
 }else return 0;
 emit(ctx,key,op,ch);
 return 1;
}
#endif
