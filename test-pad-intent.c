#include <assert.h>
#include <stdio.h>
#include "pad-intent.h"
struct sim {int mode[2],refuse,down[2],up[2];};
static int select(void *p,int d,int b){struct sim*s=p;if(s->refuse)return 0;s->mode[d]=b;return 1;}
static int mode(void *p,int d){return ((struct sim*)p)->mode[d];}
static void emit(void *p,int key,int op,int ch){struct sim*s=p;(void)key;if(op==0)s->down[ch-1]++;else s->up[ch-1]++;}
#define SEND(k,o,c,b) forward_pad_intent(&owned,k,o,c,b,&s,select,mode,emit)
int main(void){
 struct pad_intents owned={0};struct sim s={.mode={2,6},.refuse=1};
 /* Native refuses MIDI selection while a finger holds Slip Loop or Mute. */
 for(int ch=1;ch<=2;ch++){
  assert(SEND(0x411b,0,ch,3)==-1);
  assert(SEND(0x411b,2,ch,3)==0);assert(s.up[ch-1]==0);
 }
 s.refuse=0;
 assert(SEND(0x411b,0,1,3)==1);assert(SEND(0x411b,0,1,3)==0);
 assert(SEND(0x411b,0,2,1)==1);
 assert(SEND(0x411b,2,1,1)==0); /* stale other-bank release */
 assert(SEND(0x411b,2,1,3)==1);assert(s.up[0]==1&&s.up[1]==0);
 assert(SEND(0x411b,2,1,3)==0);
 s.mode[1]=6;assert(SEND(0x411b,2,2,1)==0); /* native bank changed */
 assert(owned.held[1][4]==0&&s.up[1]==0);
 assert(SEND(0x411b,0,2,1)==1);assert(SEND(0x411b,2,2,1)==1);
 puts("PASS rejected presses, stale releases, duplicate presses and deck ownership");
}
