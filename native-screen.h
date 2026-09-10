#ifndef RX3_NATIVE_SCREEN_H
#define RX3_NATIVE_SCREEN_H
#include <stdint.h>
/* Main deck-information panel (native window key136) exists before loading
 * a track too. Its visibility distinguishes the player from Browse. */
static inline int player_screen_active(void){
 void *active=*(void *volatile *)(0x024942bc+0x20);
 return active&&*(volatile int16_t*)((char*)active+6)==0;
}
static inline int main_panel_visible(void){
 if(!player_screen_active())return 0;
 uintptr_t p=*(volatile uint32_t*)0x0245b880;
 for(int i=0;p&&i<256;i++,p=*(volatile uint32_t*)(p+0x84)){
  if(*(volatile uint32_t*)(p+0xc)==136)return (*(volatile uint32_t*)(p+4)&8)!=0;
 }
 return 0;
}
#endif
