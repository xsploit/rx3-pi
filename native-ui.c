/* RX3 v1.19 native DS_GR transport strip. GUI-thread rendering only. */
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "native-ui-glyphs.h"
#include "native-screen.h"
#include "native-mixer.h"
extern char *program_invocation_short_name;
volatile int rx3_native_ui_ready=0,rx3_native_ui_pressed=-1;
static void *window;
static int disabled,shown=-1;
static int (*original_draw)(void*);
static int draw(void *arg){
 int result=original_draw(arg),show=main_panel_visible();
 rx3_mixer_draw(show);
 if(disabled)return result;
 if(!window&&show){
  uint32_t desc[13]={0};desc[2]=1280|(44u<<16);desc[3]=9;desc[5]=1; /* Smaller z draws last in DS_HW_UpdateScreen. */
  int rc=((int(*)(void**,const void*))0x1a2634)(&window,desc);
  if(rc||!window){disabled=1;write(2,"native transport window failed\n",31);return result;}
  write(2,"native transport window created\n",32);
 }
 if(!window)return result;
 if(shown!=show){((int(*)(void*,int,unsigned))0x1a061c)(window,show?1:2,8);((int(*)(void*,unsigned))0x1a0a28)(window,show?255:0);shown=show;rx3_native_ui_ready=show;}
 int pressed=rx3_native_ui_pressed;
 /* Supply the complete small surface each GUI pass, including labels
  * and pressed state, under one surface lock. */
 if(show){
  void *pixels=0;int pitch=0;
  int rc=((int(*)(void*,void**,int*))0x1a1c48)(window,&pixels,&pitch);
  if(rc||!pixels||pitch<1280*2){rx3_native_ui_ready=0;disabled=1;return result;}
  for(int y=0;y<44;y++)for(int x=0;x<1280;x++){
   unsigned c=x%142>=140?0x080808:(x/142==pressed?0x707070:0x242424);
   if(pitch>=5120)((uint32_t*)((char*)pixels+y*pitch))[x]=0xff000000|c;
   else ((uint16_t*)((char*)pixels+y*pitch))[x]=((c>>8)&0xf800)|((c>>5)&0x7e0)|((c>>3)&31);
  }
  for(unsigned i=0;i<sizeof(text_spans)/sizeof(text_spans[0]);i++){
   for(unsigned x=text_spans[i][0];x<text_spans[i][0]+text_spans[i][2];x++){
    if(pitch>=5120)((uint32_t*)((char*)pixels+text_spans[i][1]*pitch))[x]=0xffffffff;
    else ((uint16_t*)((char*)pixels+text_spans[i][1]*pitch))[x]=0xffff;
   }
  }
  ((int(*)(void*))0x1a1cb0)(window);
  ((int(*)(void*,int,int,int,int,int))0x1a0948)(window,0,0,1280,44,0x4000);
 }
 return result;
}
__attribute__((constructor))static void install_native_ui(void){
 if(!program_invocation_short_name||strcmp(program_invocation_short_name,"rbp-pi"))return;
 uint32_t *entry=(void*)0x18e75c;
 if(entry[0]!=0xe92d4ff0||entry[1]!=0xed2d8b02)return;
 long page=getpagesize();uint32_t *tr=mmap(0,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(tr==MAP_FAILED)return;
 tr[0]=entry[0];tr[1]=entry[1];tr[2]=0xe51ff004;tr[3]=0x18e764;
 if(mprotect(tr,page,PROT_READ|PROT_EXEC))return;
 syscall(0xf0002,tr,tr+4,0);original_draw=(void*)tr;
 void *base=(void*)((uintptr_t)entry&~((uintptr_t)page-1));
 if(mprotect(base,page,PROT_READ|PROT_WRITE|PROT_EXEC))return;
 entry[0]=0xe51ff004;entry[1]=(uintptr_t)draw;syscall(0xf0002,entry,entry+2,0);mprotect(base,page,PROT_READ|PROT_EXEC);
}
