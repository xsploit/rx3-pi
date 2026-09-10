/* Replace the existing WIDE artwork only in a matching 25% executable.
 * Called on the native GUI thread. Firmware image data stays in memory. */
#include <stdint.h>
#include "native-tempo25.h"
#include "native-tempo25-glyphs.h"
volatile int rx3_tempo25_artwork_state;
void rx3_tempo25_artwork_tick(void){
 if(rx3_tempo25_artwork_state)return;
 if(*(volatile uint32_t*)0x41c8e0!=25||*(volatile uint32_t*)0x4d3c2c!=25)return;
 uintptr_t base=*(volatile uint32_t*)0x05a14f60;
 if(!base)return;
 const uint8_t *record=(const void*)(base+0xca3*44);
 if(*(const uint16_t*)(record+4)!=48||*(const uint16_t*)(record+6)!=20||record[24]!=2){rx3_tempo25_artwork_state=-1;return;}
 uint32_t offset=*(const uint32_t*)(record+32);
 if(offset<5581*44||offset>0x4000000){rx3_tempo25_artwork_state=-2;return;}
 uint16_t *pixels=(void*)(base+offset);
 for(unsigned y=0;y<20;y++)for(unsigned x=0;x<47;x++)pixels[y*48+x]=tempo25_pixels[y*47+x];
 rx3_tempo25_artwork_state=1;
}
