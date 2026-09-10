#include <assert.h>
#include <stdio.h>
#include "tempo-step.h"
/* Match the firmware's float multiply then double reciprocal/truncation. */
static int quantize(float position,int range){
 float scaled=position*range;int step=rx3_tempo_step(range);
 double reciprocal=step==2?.5:(step==5?.2:.02);
 return (int)((double)scaled*reciprocal*100)*step;
}
int main(void){
 int ranges[]={6,10,16,100};float p;
 for(unsigned r=0;r<4;r++){
  int range=ranges[r],step=rx3_tempo_step(range),limit=range*100;
  for(int current=-limit;current<=limit;current+=step)for(int dir=-1;dir<=1;dir+=2){
   int expected=current+dir*step;if(expected>limit)expected=limit;if(expected<-limit)expected=-limit;
   assert(rx3_tempo_fine_position(current,range,dir,&p));assert(p>=-1&&p<=1);assert(quantize(p,range)==expected);
  }
  assert(rx3_tempo_fine_position(1,range,-1,&p)&&quantize(p,range)==0);
  assert(rx3_tempo_fine_position(-1,range,1,&p)&&quantize(p,range)==0);
 }
 assert(!rx3_tempo_fine_position(0,7,1,&p));assert(!rx3_tempo_fine_position(0,10,0,&p));
 puts("PASS all native tempo bins, endpoints, signed zero crossings and invalid ranges");
}
