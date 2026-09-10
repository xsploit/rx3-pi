/* RX3 v1.19: make the existing native pad labels act as physical pad keys.
 * Runs inside rbp-pi; all other native touch processing is preserved.
 */
#include <stdint.h>
#include "native-screen.h"
#include "mixer-state.h"
#include "native-mixer.h"
#include "native-pad-modes.h"
#include "native-mixer-layout.h"
#include "tempo-step.h"
#include "native-zoom-layout.h"
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
extern char *program_invocation_short_name;
struct touch {uint8_t down,pad[3];int x,y;};
static void (*original_touch)(void*,const struct touch*,void*);
static int held_key,held_channel,held_slider=-1,return_from_source;
static void *source_return_handler;
static int source_return_pending,source_return_frames,source_return_ready;
extern volatile int rx3_native_ui_ready,rx3_native_ui_pressed;
extern volatile int rx3_native_zoom_ready;
static void pad_key(void *handler,int key,int operation,int channel){
 void *root=*(void**)handler;
 void *manager=root?*(void**)((char*)root+0x64):0;
 if(manager)rx3_dispatch_key(manager,key,operation,channel,0,0.f,0);
}
static void slider(void *handler,int index,int x,int y){
 void *root=*(void**)handler;void *manager=root?*(void**)((char*)root+0x64):0;
 float value=mixer_slider_value(index,x,y);
 if(manager)rx3_dispatch_key(manager,rx3_mixer_bindings[index].key,index>=16?5:4,rx3_mixer_bindings[index].channel,0,index>=16?2.f*value-1.f:value,0);
}
/* Source applies its first transition asynchronously after release. Advance
 * the final Browse toggle from rendering once that transition is visible. */
void rx3_touch_navigation_tick(void){
 if(!__atomic_load_n(&source_return_pending,__ATOMIC_ACQUIRE))return;
 if(!player_screen_active()||main_panel_visible()||++source_return_frames>120){
  __atomic_store_n(&source_return_pending,0,__ATOMIC_RELEASE);return;
 }
 if(((int(*)(void))0x1126d0)()==12){source_return_ready=0;return;}
 if(++source_return_ready<3)return;
 pad_key(source_return_handler,0x202,0,0);pad_key(source_return_handler,0x202,2,0);
 __atomic_store_n(&source_return_pending,0,__ATOMIC_RELEASE);
}
static void native_touch(void *handler,const struct touch *t,void *mode){
 if(held_slider>=0){if(!main_panel_visible()||!rx3_mixer_visible){held_slider=-1;held_key=t->down?-1:0;return;}if(t->down)slider(handler,held_slider,t->x,t->y);else held_slider=-1;return;}
 if(held_key){
  if(!t->down){
   if(held_key>0)pad_key(handler,held_key,2,held_channel);
   if(return_from_source){
    source_return_handler=handler;source_return_frames=0;source_return_ready=0;
    __atomic_store_n(&source_return_pending,1,__ATOMIC_RELEASE);
   }
   return_from_source=0;held_key=0;rx3_native_ui_pressed=-1;
  }
  return;
 }
 int main_visible=main_panel_visible();
 if(t->down&&!*((uint8_t*)handler+4)&&player_screen_active()){
  if(rx3_native_ui_ready&&t->y>=0&&t->y<44&&t->x>=0&&t->x<1280&&(main_visible||t->x>=580)){
   static const int keys[9]={0x202,0x4101,0x4102,0x4112,0x4101,0x4102,0x4112,-1,0x201};
   static const int channels[9]={0,1,1,1,2,2,2,0,0};
   int i=t->x/142;if(i>8)i=8;held_key=keys[i];held_channel=channels[i];rx3_native_ui_pressed=i;
   if(!main_visible){
    static const int navkeys[7]={0x205,0x203,0x420e,0x202,0x420d,0x201,0x20b};
    i=(t->x-580)/100;held_key=navkeys[i];held_channel=0;rx3_native_ui_pressed=10+i;
    int browse_mode=((int(*)(void))0x1126d0)(),tag_list=browse_mode==4;
    /* Finish Source->Browse->Player on release after the first transition. */
    return_from_source=i==3&&browse_mode==12;
    if(i==3&&tag_list)held_key=0x203; /* Close Tag List directly to player. */
    if(i==1&&tag_list){held_key=-1;return;}
    pad_key(handler,held_key,0,0);
    if(i==2&&tag_list)pad_key(handler,held_key,1,0);
    return;
   }
   if(i==7)rx3_mixer_visible=!rx3_mixer_visible;else pad_key(handler,held_key,0,held_channel);return;
  }
  if(!main_visible){original_touch(handler,t,mode);return;}
  int zoom_direction=rx3_zoom_direction_at(t->x,t->y);
  if(rx3_native_zoom_ready&&!rx3_mixer_visible&&!((int(*)(void))0x17f8a0)()&&zoom_direction){
   held_key=-1;rx3_native_ui_pressed=zoom_direction<0?20:21;
   void *root=*(void**)handler;void *manager=root?*(void**)((char*)root+0x64):0;
   if(manager)rx3_dispatch_key(manager,0x420c,4,0,zoom_direction,0.f,0);
   return;
  }
  if(rx3_mixer_visible){
   int header_channel=0,header_key=mixer_header_key_at(t->x,t->y,&header_channel);
   if(header_key){held_key=header_key;held_channel=header_channel;pad_key(handler,held_key,0,held_channel);return;}
   int direction=0,fine=mixer_tempo_step_at(t->x,t->y,&direction);
   if(fine>=0){
    int deck=fine-16;float position;held_key=-1;
    int current=((int(*)(int))0xfd2dc)(deck),range=((int(*)(int))0xfd2b4)(deck);
    float catchup=0;int pickup=0;
    /* Native tempo target is valid while Sync or post-Sync pickup holds tempo.
     * Keep active Sync under native control. After it is off, catch the held
     * playback tempo before applying the requested fine step. */
    if(((unsigned(*)(int))0xfd28c)(deck)!=0xffffffffu&&!((int(*)(int))0xfde60)(deck)){
     pickup=rx3_tempo_pickup_from_snapshot(((unsigned(*)(int))0xfd1fc)(deck),((unsigned(*)(int))0xfd244)(deck),range,current,&current,&catchup);
     if(!pickup)return; /* A held tempo outside this range cannot be caught. */
    }
    if(rx3_tempo_fine_position(current,range,direction,&position)){
     void *root=*(void**)handler;void *manager=root?*(void**)((char*)root+0x64):0;
     if(manager){
      if(pickup)rx3_dispatch_key(manager,0x4109,5,deck+1,0,catchup,0);
      rx3_dispatch_key(manager,0x4109,5,deck+1,0,position,0);
     }
    }
    return;
   }
   int index=mixer_slider_at(t->x,t->y);
   if(index>=0){held_slider=index;slider(handler,held_slider,t->x,t->y);}
   else if(t->y>=694&&t->y<764&&((t->x>=32&&t->x<432)||(t->x>=848&&t->x<1248))){held_key=0x5020;held_channel=t->x<640?1:2;pad_key(handler,held_key,0,held_channel);}
   else held_key=-1; /* Consume blank-panel gestures through release. */
   return;
  }
  if(rx3_pad_modes_ready&&t->y>=492&&t->y<518&&t->x>=0&&t->x<1280){
   int deck=t->x/640,local=t->x%640-10,col=local/158;
   held_key=-1;
   if(local>=0&&col>=0&&col<4&&local%158<150){held_key=0x4113+col;held_channel=deck+1;pad_key(handler,held_key,0,held_channel);}
   return;
  }
  int row=t->y>=518&&t->y<=540?0:(t->y>=548&&t->y<=570?1:-1);
  int deck=t->x/640,local=t->x%640-10,col=local/158;
  if(row>=0&&deck>=0&&deck<2&&local>=0&&col>=0&&col<4&&local%158<150){
   held_key=0x4117+row*4+col;held_channel=deck+1;
   pad_key(handler,held_key,0,held_channel);
   const char msg[]="native pad touch dispatched\n";write(2,msg,sizeof(msg)-1);
   return;
  }
 }
 if(rx3_mixer_visible&&main_visible&&t->y>=44)return;
 original_touch(handler,t,mode);
}
__attribute__((constructor))static void install_native_touch(void){
 if(!program_invocation_short_name||strcmp(program_invocation_short_name,"rbp-pi"))return;
 uint32_t *entry=(uint32_t*)0x2dc104;
 if(entry[0]!=0xe92d45f0||entry[1]!=0xe1a06002)return;
 long page=getpagesize();
 uint32_t *trampoline=mmap(0,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(trampoline==MAP_FAILED)return;
 trampoline[0]=entry[0];trampoline[1]=entry[1];
 trampoline[2]=0xe51ff004;trampoline[3]=0x2dc10c;
 if(mprotect(trampoline,page,PROT_READ|PROT_EXEC))return;
 syscall(0xf0002,trampoline,trampoline+4,0);
 original_touch=(void*)trampoline;
 void *code_page=(void*)((uintptr_t)entry&~((uintptr_t)page-1));
 if(mprotect(code_page,page,PROT_READ|PROT_WRITE|PROT_EXEC))return;
 entry[0]=0xe51ff004;entry[1]=(uint32_t)(uintptr_t)native_touch;
 syscall(0xf0002,entry,entry+2,0);
 mprotect(code_page,page,PROT_READ|PROT_EXEC);
}
