/* Deck-specific grid nudges execute on the native GUI thread. */
#include <stdint.h>
#include "native-grid.h"
#include "native-screen.h"
struct grid_command {int channel,delta;uint32_t music[2];};
static struct grid_command queue[64];
static unsigned head,tail;
static void music_id(int deck,uint32_t id[2]){((void(*)(int,void*))0x1842f4)(deck,id);}
void rx3_grid_enqueue(int channel,int delta){
 if(channel<1||channel>2||!delta||delta < -100||delta>100)return;
 unsigned h=__atomic_load_n(&head,__ATOMIC_RELAXED),next=(h+1)%64;
 if(next==__atomic_load_n(&tail,__ATOMIC_ACQUIRE))return;
 struct grid_command c={.channel=channel,.delta=delta};music_id(channel-1,c.music);
 queue[h]=c;__atomic_store_n(&head,next,__ATOMIC_RELEASE);
}
void rx3_grid_tick(void){
 /* The native save request has shared staging storage. Give its worker a
  * render interval between requests rather than issuing a whole FIFO burst. */
 for(unsigned count=0;count<1;count++){
  unsigned t=__atomic_load_n(&tail,__ATOMIC_RELAXED);
  if(t==__atomic_load_n(&head,__ATOMIC_ACQUIRE))return;
  struct grid_command c=queue[t];__atomic_store_n(&tail,(t+1)%64,__ATOMIC_RELEASE);
  if(!player_screen_active())continue;
  uint32_t current[2];music_id(c.channel-1,current);
  if(current[0]!=c.music[0]||current[1]!=c.music[1])continue;
  if(!((int(*)(int))0x18431c)(c.channel-1))continue;
  int previous=((int(*)(void))0x1341d8)();
  int grid_mode=((int(*)(void))0x17f8a0)();
  ((void(*)(int))0x134208)(c.channel);
  /* GridAdjust alone changes the live offset. The native GRID lifecycle
   * snapshots the music identity and commits its save request on exit.
   * Complete that lifecycle within this GUI callback when GRID is hidden;
   * the existing visible GRID session retains its own save lifecycle. */
  if(!grid_mode){
   ((void(*)(int))0x17f88c)(1);
   ((void(*)(void))0x133bdc)();
  }
  ((int(*)(int))0x133744)(c.delta);
  if(!grid_mode){
   ((void(*)(void))0x133bdc)();
   ((void(*)(int))0x17f88c)(0);
   ((void(*)(void))0x133bdc)();
  }
  ((void(*)(int))0x134208)(previous);
 }
}
