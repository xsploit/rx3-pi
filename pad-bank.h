#ifndef RX3_PAD_BANK_H
#define RX3_PAD_BANK_H
/* Selector presses toggle the second bank. Wait for actual native state. */
static int select_pad_bank(int deck,int target,void *ctx,
 int (*get)(void*,int),void (*press)(void*,int,int),void (*wait)(void*)){
 if(deck<0||deck>1||target<0||target>7)return 0;
 for(int attempt=0;attempt<2;attempt++){
  int current=get(ctx,deck);if(current==target)return 1;
  if(current<0||current>7)return 0;
  int expected=(current%4==target%4)?(current^4):(target%4);
  press(ctx,0x4113+target%4,deck+1);
  int tries=0;
  while(get(ctx,deck)!=expected&&tries++<25)wait(ctx);
  if(get(ctx,deck)!=expected)return 0;
 }
 return get(ctx,deck)==target;
}
#endif
