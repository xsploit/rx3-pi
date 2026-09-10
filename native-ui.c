/* RX3 v1.19 native DS_GR transport strip. GUI-thread rendering only. */
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "native-ui-glyphs.h"
#include "native-screen.h"
#include "native-mixer.h"
#include "native-pad-modes.h"
extern char *program_invocation_short_name;
volatile int rx3_native_ui_ready=0,rx3_native_ui_pressed=-1;
/* Native window keys also determine stacking and must be unique:
 * player strip1, mixer2, compact navigation3, pad selectors4. */
struct surface {void *window;int shown,painted,last_pressed,last_tag_list;};
static struct surface surfaces[2]={{0,-1},{0,-1}};
static int disabled;
volatile int rx3_ui_failure[4];
static int (*original_draw)(void*);
static int paint(int navigation,int show){
 struct surface *s=&surfaces[navigation];int width=navigation?600:1280,cell=navigation?100:142;
 if(!s->window&&show){
  uint32_t desc[13]={0};desc[2]=width|(44u<<16);desc[3]=9;desc[5]=navigation?3:1;desc[7]=navigation?680:0;
  int rc=((int(*)(void**,const void*))0x1a2634)(&s->window,desc);
  if(rc||!s->window){rx3_ui_failure[0]=1;rx3_ui_failure[1]=rc;rx3_ui_failure[2]=navigation;return 0;}
 }
 if(!s->window)return 1;
 if(s->shown!=show){
  ((int(*)(void*,int,unsigned))0x1a061c)(s->window,show?1:2,8);
  ((int(*)(void*,unsigned))0x1a0a28)(s->window,show?255:0);s->shown=show;s->painted=0;
 }
 if(!show)return 1;
 int tag_list=navigation&&((int(*)(void))0x1126d0)()==4;
 int pressed=rx3_native_ui_pressed-(navigation?10:0);
 if(s->painted&&s->last_pressed==pressed&&s->last_tag_list==tag_list)return 1;
 void *pixels=0;int pitch=0;
 int rc=((int(*)(void*,void**,int*))0x1a1c48)(s->window,&pixels,&pitch);
 if(rc){rx3_ui_failure[0]=2;rx3_ui_failure[1]=rc;rx3_ui_failure[2]=navigation;return 0;}
 if(!pixels||pitch<width*2){rx3_ui_failure[0]=3;rx3_ui_failure[1]=pitch;rx3_ui_failure[2]=navigation;rx3_ui_failure[3]=(int)(uintptr_t)pixels;((int(*)(void*))0x1a1cb0)(s->window);return 0;}
 /* These format9 surfaces use RGB565. Row pitch may include padding. */
 for(int y=0;y<44;y++)for(int x=0;x<width;x++){
  unsigned c=x%cell>=cell-2?0x080808:(x/cell==pressed?0x707070:0x242424);
  ((uint16_t*)((char*)pixels+y*pitch))[x]=((c>>8)&0xf800)|((c>>5)&0x7e0)|((c>>3)&31);
 }
 const unsigned short (*spans)[3]=navigation?navigation_spans:text_spans;
 unsigned count=navigation?sizeof(navigation_spans)/sizeof(navigation_spans[0]):sizeof(text_spans)/sizeof(text_spans[0]);
 for(unsigned i=0;i<count;i++)for(unsigned x=spans[i][0];x<spans[i][0]+spans[i][2];x++)
  ((uint16_t*)((char*)pixels+spans[i][1]*pitch))[x]=0xffff;
 if(navigation){
  const unsigned short (*tag)[3]=tag_list?navigation_tag_remove_spans:navigation_tag_add_spans;
  unsigned n=tag_list?sizeof(navigation_tag_remove_spans)/sizeof(tag[0]):sizeof(navigation_tag_add_spans)/sizeof(tag[0]);
  for(unsigned i=0;i<n;i++)for(unsigned x=tag[i][0];x<tag[i][0]+tag[i][2];x++)
   ((uint16_t*)((char*)pixels+tag[i][1]*pitch))[x]=0xffff;
 }
 ((int(*)(void*))0x1a1cb0)(s->window);
 ((int(*)(void*,int,int,int,int,int))0x1a0948)(s->window,0,0,width,44,0x4000);
 s->painted=1;s->last_pressed=pressed;s->last_tag_list=tag_list;
 return 1;
}
static int draw(void *arg){
 int result=original_draw(arg),main=main_panel_visible(),show=player_screen_active();
 rx3_mixer_draw(main);
 rx3_pad_modes_draw(main&&show&&!rx3_mixer_visible);
 int ok1=paint(0,!disabled&&show&&main),ok2=paint(1,!disabled&&show&&!main);
 if(!ok1||!ok2)disabled=1;
 rx3_native_ui_ready=!disabled&&show;
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
