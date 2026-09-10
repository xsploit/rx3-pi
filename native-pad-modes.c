/* Native pad mode selectors in the existing header space above each pad bank. */
#include <stdint.h>
#include "native-pad-modes.h"
#include "native-pad-mode-glyphs.h"
volatile int rx3_pad_modes_ready;
static void *window;
static int shown=-1,painted,last[2],failed;
void rx3_pad_modes_draw(int visible){
 if(failed)visible=0;
 if(!window&&visible){
  uint32_t d[13]={0};d[2]=1280|(26u<<16);d[3]=9;d[5]=4;d[8]=492;
  if(((int(*)(void**,const void*))0x1a2634)(&window,d)||!window){failed=1;return;}
 }
 if(!window)return;
 if(shown!=visible){((int(*)(void*,int,unsigned))0x1a061c)(window,visible?1:2,8);((int(*)(void*,unsigned))0x1a0a28)(window,visible?255:0);shown=visible;painted=0;}
 rx3_pad_modes_ready=visible;
 if(!visible)return;
 int mode[2]={((int(*)(int))0xfd3cc)(0),((int(*)(int))0xfd3cc)(1)};
 if(painted&&mode[0]==last[0]&&mode[1]==last[1])return;
 void *pixels=0;int pitch=0;
 if(((int(*)(void*,void**,int*))0x1a1c48)(window,&pixels,&pitch)){failed=1;rx3_pad_modes_ready=0;return;}
 if(!pixels||pitch<2560){((int(*)(void*))0x1a1cb0)(window);failed=1;rx3_pad_modes_ready=0;return;}
 for(int y=0;y<26;y++)for(int x=0;x<1280;x++){
  int deck=x/640,local=x%640-10,col=local/158;
  uint16_t color=0x0821; /* Native RGB565 zero is a transparent color key. */
  if(local>=0&&col<4&&local%158<150&&y>=1&&y<25)color=(mode[deck]>=0&&mode[deck]<8&&mode[deck]%4==col)?0x039f:0x2104;
  ((uint16_t*)((char*)pixels+y*pitch))[x]=color;
 }
 for(unsigned i=0;i<sizeof(pad_mode_spans)/sizeof(pad_mode_spans[0]);i++){
  const unsigned short *s=pad_mode_spans[i];for(unsigned x=s[0];x<s[0]+s[2];x++)((uint16_t*)((char*)pixels+s[1]*pitch))[x]=0xffff;
 }
 for(int deck=0;deck<2;deck++)if(mode[deck]>=4&&mode[deck]<8){
  int left=deck*640+10+(mode[deck]%4)*158+133;
  for(unsigned i=0;i<sizeof(pad_bank_two_spans)/sizeof(pad_bank_two_spans[0]);i++){
   const unsigned short*s=pad_bank_two_spans[i];for(unsigned x=s[0];x<s[0]+s[2];x++)((uint16_t*)((char*)pixels+s[1]*pitch))[left+x]=0xffff;
  }
 }
 ((int(*)(void*))0x1a1cb0)(window);
 ((int(*)(void*,int,int,int,int,int))0x1a0948)(window,0,0,1280,26,0x4000);
 last[0]=mode[0];last[1]=mode[1];painted=1;
}
