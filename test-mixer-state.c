#include "mixer-state.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
int main(void){
 struct rx3_mixer_snapshot s;rx3_mixer_snapshot(&s);assert(s.valid==0&&s.cue==0);
 for(int i=0;i<16;i++)rx3_mixer_observe(rx3_mixer_bindings[i].key,4,rx3_mixer_bindings[i].channel,i/16.f);
 rx3_mixer_snapshot(&s);assert(s.valid==65535);
 for(int i=0;i<16;i++)assert(s.levels[i]==i/16.f);
 unsigned revision=s.revision;
 rx3_mixer_observe(0x501e,4,1,NAN);rx3_mixer_observe(0x501e,4,1,INFINITY);
 rx3_mixer_observe(0x501e,4,1,-.1f);rx3_mixer_observe(0x501e,4,3,.5f);
 rx3_mixer_observe(0x4109,4,1,.5f);rx3_mixer_observe(0x4109,5,1,NAN);
 rx3_mixer_observe(0x4109,5,1,1.1f);rx3_mixer_snapshot(&s);assert(s.revision==revision);
 rx3_mixer_observe(0x4109,5,1,-.5f);rx3_mixer_observe(0x4109,5,2,1.f);
 rx3_mixer_snapshot(&s);assert(s.valid==((1u<<18)-1));assert(s.levels[16]==.25f&&s.levels[17]==1.f);
 rx3_mixer_observe(0x4109,5,1,0.f);rx3_mixer_observe(0x4109,5,2,-1.f);
 rx3_mixer_snapshot(&s);assert(s.levels[16]==.5f&&s.levels[17]==0.f);
 rx3_mixer_observe(0x5020,0,1,0);rx3_mixer_observe(0x5020,0,1,0);rx3_mixer_snapshot(&s);assert(s.cue==1);
 rx3_mixer_observe(0x5020,2,1,0);rx3_mixer_observe(0x5020,0,2,0);rx3_mixer_snapshot(&s);assert(s.cue==3);
 rx3_mixer_observe(0x5020,0,1,0);rx3_mixer_snapshot(&s);assert(s.cue==2);
 puts("All 18 controls, invalid inputs, channel separation and cue press/release passed.");return 0;
}
