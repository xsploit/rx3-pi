/* RX3 v1.19: make the existing native pad labels act as physical pad keys.
 * Runs inside rbp-pi; all other native touch processing is preserved.
 */
#include <stdint.h>
#include "native-screen.h"
#include "mixer-state.h"
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
extern char *program_invocation_short_name;
struct touch {uint8_t down,pad[3];int x,y;};
static void (*original_touch)(void*,const struct touch*,void*);
static int held_key,held_channel;
extern volatile int rx3_native_ui_ready,rx3_native_ui_pressed;
static void pad_key(void *handler,int key,int operation,int channel){
 void *root=*(void**)handler;
 void *manager=root?*(void**)((char*)root+0x64):0;
 if(manager)rx3_dispatch_key(manager,key,operation,channel,0,0.f,0);
}
static void native_touch(void *handler,const struct touch *t,void *mode){
 if(held_key){
  if(!t->down){pad_key(handler,held_key,2,held_channel);held_key=0;rx3_native_ui_pressed=-1;}
  return;
 }
 int main_visible=main_panel_visible();
 if(t->down&&!*((uint8_t*)handler+4)&&main_visible){
  if(rx3_native_ui_ready&&t->y>=0&&t->y<44&&t->x>=0&&t->x<1280){
   static const int keys[8]={0x202,0x4101,0x4102,0x4112,0x4101,0x4102,0x4112,0x201};
   static const int channels[8]={0,1,1,1,2,2,2,0};
   int i=t->x/160;held_key=keys[i];held_channel=channels[i];rx3_native_ui_pressed=i;
   pad_key(handler,held_key,0,held_channel);return;
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
