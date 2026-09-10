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
static int last_tempo[2],last_range[2],last_lock[2];
static unsigned last_bpm[2];
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
static void tempo_string(int center,int y,const char *text,unsigned n){
 int x=center-(int)n*4;
 for(unsigned d=0;d<n;d++)for(unsigned i=0;i<sizeof(tempo_text)/sizeof(tempo_text[0]);i++)
  if(tempo_text[i][0]==(unsigned)text[d])box(x+d*8+tempo_text[i][1],y+tempo_text[i][2],tempo_text[i][3],1,0xffff);
}
static void tempo_number(int center,int y,int rate){
 char text[8];unsigned n=0,a=rate<0?-rate:rate;
 text[n++]=rate<0?'-':'+';
 if(a>=10000)text[n++]='0'+a/10000;
 if(a>=1000)text[n++]='0'+a/1000%10;
 text[n++]='0'+a/100%10;text[n++]='.';
 text[n++]='0'+a/10%10;text[n++]='0'+a%10;
 tempo_string(center,y,text,n);
}
/* Effective BPM is separate from the fader setting during native Sync/pickup. */
static void bpm_number(int center,unsigned bpm){
 char text[8];unsigned n=0;
 if(!bpm||bpm>=100000){text[n++]='-';text[n++]='-';text[n++]='-';}
 else {
  unsigned a=bpm/10; /* Native display truncates to tenths. */
  if(a>=1000)text[n++]='0'+a/1000;
  if(a>=100)text[n++]='0'+a/100%10;
  text[n++]='0'+a/10%10;text[n++]='.';text[n++]='0'+a%10;
 }
 text[n++]='B';text[n++]='P';text[n++]='M';
 tempo_string(center,134,text,n);
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
 unsigned bpm[2]={((unsigned(*)(int))0xfd1fc)(0),((unsigned(*)(int))0xfd1fc)(1)};
 int range[2]={((int(*)(int))0xfd2b4)(0),((int(*)(int))0xfd2b4)(1)};
 int keylock[2]={((int(*)(int))0xfd30c)(0),((int(*)(int))0xfd30c)(1)};
 if(painted&&bpm[0]==last_bpm[0]&&bpm[1]==last_bpm[1]&&revision==state.revision&&tempo[0]==last_tempo[0]&&tempo[1]==last_tempo[1]&&range[0]==last_range[0]&&range[1]==last_range[1]&&keylock[0]==last_lock[0]&&keylock[1]==last_lock[1])return;
 for(unsigned i=0;i<1280*756;i++)canvas[i]=0x1082;
 box(0,0,480,54,0x018e);box(480,0,320,54,0x2945);box(800,0,480,54,0x018e);
 for(int deck=0;deck<2;deck++){
  int base=deck*800;
  box(base+148,8,160,38,0x2945);box(base+312,8,164,38,keylock[deck]?0x04bf:0x2945);
  int found=0;
  for(unsigned i=0;i<sizeof(tempo_range_text)/sizeof(tempo_range_text[0]);i++)if(tempo_range_text[i][0]==range[deck]){
   box(base+224+tempo_range_text[i][1],6+tempo_range_text[i][2],tempo_range_text[i][3],1,0xffff);found=1;
  }
  if(!found){box(base+250,26,10,2,0xffff);box(base+266,26,10,2,0xffff);}
 }
 for(int i=0;i<RX3_MIXER_COUNT;i++){
  if(i==7)continue;
  int x=mixer_column_center(i)-40;float v=state.levels[i];if(v<0)v=0;if(v>1)v=1;
  box(x+38,160,4,390,0x528a);box(x+20,354,40,2,0x528a);
  if(state.valid&(1u<<i)){
   int y=550-(int)(v*390+.5f);
   box(x+36,y,8,550-y,0x04bf);box(x+12,y-7,56,14,0xe73c);
   if(i>=16){tempo_number(x+40,103,tempo[i-16]);bpm_number(x+40,bpm[i-16]);}
   else number(x+22,110,(unsigned)(v*100+.5f));
  }
 }
 for(int i=16;i<18;i++){
  int x=mixer_column_center(i)-34;
  box(x,554,32,34,0x2945);box(x+36,554,32,34,0x2945);
  box(x+8,570,16,2,0xffff);box(x+44,570,16,2,0xffff);box(x+51,563,2,16,0xffff);
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
 revision=state.revision;last_tempo[0]=tempo[0];last_tempo[1]=tempo[1];
 for(int i=0;i<2;i++){last_bpm[i]=bpm[i];last_range[i]=range[i];last_lock[i]=keylock[i];}
 painted=1;
}
