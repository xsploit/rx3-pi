#include <assert.h>
#include <stdio.h>
#include "pad-bank.h"
struct sim{int state,pending,ticks,presses,failed;};
static int get(void *p,int d){assert(d==0);return ((struct sim*)p)->state;}
static void press(void *p,int key,int ch){struct sim*s=p;assert(ch==1);int family=key-0x4113;assert(family>=0&&family<4);s->pending=s->state%4==family?s->state^4:family;s->ticks=3;s->presses++;}
static void wait(void *p){struct sim*s=p;if(!s->failed&&!--s->ticks)s->state=s->pending;}
int main(void){
 for(int a=0;a<8;a++)for(int b=0;b<8;b++){
  struct sim s={.state=a};assert(select_pad_bank(0,b,&s,get,press,wait));assert(s.state==b);assert(s.presses<=2);if(a==b)assert(s.presses==0);
 }
 struct sim failed={.state=7,.failed=1};assert(!select_pad_bank(0,3,&failed,get,press,wait));assert(failed.presses==1);
 puts("PASS all 64 bank transitions and missing acknowledgment");
}
