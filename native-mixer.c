#include <stdint.h>
#include <string.h>
#include "mixer-state.h"
#include "native-mixer.h"
#include "native-mixer-layout.h"
#include "native-mixer-glyphs.h"
volatile int rx3_mixer_visible;
static void *window;
static int shown,disabled,painted;
static uint32_t revision;
static int last_tempo[2];
static uint16_t canvas[1280*756];
static void box(int x,int y,int w,int h,uint16_t color){
 for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)canvas[yy*1280+xx]=color;
}
static void number(int x,int y,unsigned n){
 unsigned digits[3]={n/100,(n/10)%10,n%10};
 for(int d=0;d<3;d++){
  if(d==0&&!digits[0])continue;
  if(d==1&&!digits[0]&&!digits[1])continue;
  for(unsigned i=0;i<sizeof(mixer_digits)/sizeof(mixer_digits[0]);i++)if(mixer_digits[i][0]==digits[d])
   box(x+d*12+mixer_digits[i][1],y+mixer_digits[i][2],mixer_digits[i][3],1,0xffff);
 }
}
static void tempo_number(int center,int y,int rate){
 char text[8];unsigned n=0,a=rate<0?-rate:rate;
 text[n++]=rate<0?'-':'+';
 if(a>=10000)text[n++]='0'+a/10000;
 if(a>=1000)text[n++]='0'+a/1000%10;
 text[n++]='0'+a/100%10;text[n++]='.';
 text[n++]='0'+a/10%10;text[n++]='0'+a%10;
 int x=center-(int)n*4;
 for(unsigned d=0;d<n;d++)for(unsigned i=0;i<sizeof(tempo_text)/sizeof(tempo_text[0]);i++)
  if(tempo_text[i][0]==(unsigned)text[d])box(x+d*8+tempo_text[i][1],y+tempo_text[i][2],tempo_text[i][3],1,0xffff);
}
void rx3_mixer_draw(int main_visible){
 if(!main_visible)rx3_mixer_visible=0;
 int show=main_visible&&rx3_mixer_visible;
 if(disabled){rx3_mixer_visible=0;show=0;}
 if(!window&&show){
  uint32_t desc[13]={0};desc[2]=1280|(756u<<16);desc[3]=9;desc[5]=2;desc[8]=44;
  if(((int(*)(void**,const void*))0x1a2634)(&window,desc)||!window){disabled=1;rx3_mixer_visible=0;return;}
 }
 if(!window)return;
 if(shown!=show){
  ((int(*)(void*,int,unsigned))0x1a061c)(window,show?1:2,8);
  ((int(*)(void*,unsigned))0x1a0a28)(window,show?255:0);
  shown=show;painted=0;
 }
 if(!show)return;
 struct rx3_mixer_snapshot state;rx3_mixer_snapshot(&state);
 int tempo[2]={((int(*)(int))0xfd2dc)(0),((int(*)(int))0xfd2dc)(1)};
 if(painted&&revision==state.revision&&tempo[0]==last_tempo[0]&&tempo[1]==last_tempo[1])return;
 for(unsigned i=0;i<1280*756;i++)canvas[i]=0x1082;
 box(0,0,480,54,0x018e);box(480,0,320,54,0x2945);box(800,0,480,54,0x018e);
 for(int i=0;i<RX3_MIXER_COUNT;i++){
  if(i==7)continue;
  int x=mixer_column_center(i)-40;float v=state.levels[i];if(v<0)v=0;if(v>1)v=1;
  box(x+38,160,4,390,0x528a);box(x+20,354,40,2,0x528a);
  if(state.valid&(1u<<i)){
   int y=550-(int)(v*390+.5f);
   box(x+36,y,8,550-y,0x04bf);box(x+12,y-7,56,14,0xe73c);
   if(i>=16)tempo_number(x+40,110,tempo[i-16]);
   else number(x+22,110,(unsigned)(v*100+.5f));
  }
 }
 box(80,606,1120,4,0x528a);box(638,592,4,32,0x528a);
 if(state.valid&(1u<<7)){
  float v=state.levels[7];if(v<0)v=0;if(v>1)v=1;
  int x=80+(int)(v*1120+.5f);
  box(80,604,x-80,8,0x04bf);box(x-10,592,20,32,0xe73c);
 }
 box(32,650,400,70,state.cue&1?0x04bf:0x4208);
 box(848,650,400,70,state.cue&2?0x04bf:0x4208);
 for(unsigned i=0;i<sizeof(mixer_text)/sizeof(mixer_text[0]);i++)box(mixer_text[i][0],mixer_text[i][1],mixer_text[i][2],1,0xffff);
 void *pixels=0;int pitch=0;
 int rc=((int(*)(void*,void**,int*))0x1a1c48)(window,&pixels,&pitch);
 if(rc)return;
 if(!pixels||pitch<2560){((int(*)(void*))0x1a1cb0)(window);disabled=1;rx3_mixer_visible=0;return;}
 for(int y=0;y<756;y++){
  if(pitch<5120)memcpy((char*)pixels+y*pitch,canvas+y*1280,2560);
  else for(int x=0;x<1280;x++){uint32_t c=canvas[y*1280+x];((uint32_t*)((char*)pixels+y*pitch))[x]=0xff000000|((c&0xf800)<<8)|((c&0x7e0)<<5)|((c&31)<<3);}
 }
 ((int(*)(void*))0x1a1cb0)(window);
 ((int(*)(void*,int,int,int,int,int))0x1a0948)(window,0,0,1280,756,0x4000);
 revision=state.revision;last_tempo[0]=tempo[0];last_tempo[1]=tempo[1];painted=1;
}
