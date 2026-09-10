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
 int ranges[]={6,10,16,25,100};float p;
 for(unsigned r=0;r<5;r++){
  int range=ranges[r],step=rx3_tempo_step(range),limit=range*100;
  for(int current=-limit;current<=limit;current+=step)for(int dir=-1;dir<=1;dir+=2){
   int expected=current+dir*step;if(expected>limit)expected=limit;if(expected<-limit)expected=-limit;
   assert(rx3_tempo_fine_position(current,range,dir,&p));assert(p>=-1&&p<=1);assert(quantize(p,range)==expected);
  }
  assert(rx3_tempo_fine_position(1,range,-1,&p)&&quantize(p,range)==0);
  assert(rx3_tempo_fine_position(-1,range,1,&p)&&quantize(p,range)==0);
 }
 assert(!rx3_tempo_fine_position(0,7,1,&p));assert(!rx3_tempo_fine_position(0,10,0,&p));
 int held;
 assert(rx3_tempo_pickup_position(9772,9307,10,0,&held,&p)&&held==500&&quantize(p,10)==500);
 assert(rx3_tempo_pickup_position(8842,9307,10,0,&held,&p)&&held==-500&&quantize(p,10)==-500);
 for(unsigned r=0;r<5;r++){
  int range=ranges[r],step=rx3_tempo_step(range);
  for(int rate=-range*100+step;rate<=range*100;rate+=step){
   /* 100 BPM gives exact BPM hundredths for every native tempo bin. */
   assert(rx3_tempo_pickup_position(10000+rate,10000,range,0,&held,&p));
   assert(held==rate&&quantize(p,range)==rate);
  }
 }
 assert(!rx3_tempo_pickup_position(20000,10000,6,0,&held,&p));
 assert(!rx3_tempo_pickup_position(0xffffffffu,10000,10,0,&held,&p));
 assert(!rx3_tempo_pickup_position(10000,0,10,0,&held,&p));
 /* Off-grid 126.05 BPM track held at 93.07: nearest -26%, but catch
  * must cross -26.16% before stepping back up toward -25.5%. */
 assert(rx3_tempo_pickup_position(9307,12605,100,0,&held,&p)&&held==-2600&&quantize(p,100)==-2650);
 assert(rx3_tempo_pickup_position(9307,12605,100,-5000,&held,&p)&&held==-2600&&quantize(p,100)==-2600);
 assert(rx3_tempo_pickup_position(12605,9307,100,0,&held,&p)&&held==3550&&quantize(p,100)==3550);
 assert(rx3_tempo_pickup_position(12605,9307,100,5000,&held,&p)&&held==3550&&quantize(p,100)==3500);
 /* Snapshot values include +5 display bias. A held 99 BPM on a 100
  * BPM track is exactly -1%; from below, catch at -1%, not -0.98%. */
 assert(rx3_tempo_pickup_from_snapshot(9905,10005,6,-200,&held,&p));
 assert(held==-100&&quantize(p,6)==-100);
 assert(rx3_tempo_pickup_position(9905,10005,6,-200,&held,&p));
 assert(quantize(p,6)==-98); /* Demonstrates the old wrong-side catch. */
 assert(rx3_tempo_pickup_from_snapshot(10105,10005,6,200,&held,&p));
 assert(held==100&&quantize(p,6)==100);
 assert(!rx3_tempo_pickup_from_snapshot(5,10005,6,0,&held,&p));
 assert(!rx3_tempo_pickup_from_snapshot(9905,5,6,0,&held,&p));
 assert(!rx3_tempo_pickup_from_snapshot(0xffffffffu,10005,6,0,&held,&p));
 puts("PASS all native tempo bins, endpoints, signed zero crossings and invalid ranges");
}
