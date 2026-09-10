#ifndef RX3_TEMPO_STEP_H
#define RX3_TEMPO_STEP_H
/* RX3 v1.19 Tempo::STEP_TBL_: percentage hundredths per native step. */
static int rx3_tempo_step(int range){return range==6?2:(range==10||range==16||range==25?5:(range==100?50:0));}
/* Quantize held playback tempo to the nearest available slider step.
 * BPM units are hundredths. Refuse invalid or out-of-range held tempos. */
static int rx3_tempo_pickup_position(unsigned bpm,unsigned original,int range,int current,int *rate,float *position){
 int step=rx3_tempo_step(range);
 if(!step||!rate||!position||!bpm||bpm>=100000||!original||original>=100000)return 0;
 double effective=((double)bpm/original-1.)*10000.;
 if(effective>range*100.+1.||effective<-range*100.-1.)return 0;
 int steps=(int)(effective/step+(effective<0?-.5:.5));
 int target=steps*step,limit=range*100;
 if(target>limit)target=limit;
 if(target<-limit)target=-limit;
 *rate=target;
 /* The nearest bin may remain on the uncaught side of an off-grid held
  * tempo. Cross toward the held speed from the current fader position. */
 int catchup=(int)(effective/step)*step;
 if(effective>current&&catchup<effective-.000001)catchup+=step;
 if(effective<current&&catchup>effective+.000001)catchup-=step;
 if(catchup>limit)catchup=limit;
 if(catchup<-limit)catchup=-limit;
 *position=!catchup?0.f:(catchup==limit?1.f:(catchup==-limit?-1.f:(catchup+(catchup>0?step*.25f:-step*.25f))/limit));
 return 1;
}
/* UiGetPlayBpm/UiGetPlayOriginalBpm contain a +5 bias for tenths display
 * rounding (PlayerInnards::getStat at 0x30164c/0x301664). Undo that bias
 * before calculating a speed ratio; leave display callers unchanged. */
static int rx3_tempo_pickup_from_snapshot(unsigned bpm,unsigned original,int range,int current,int *rate,float *position){
 if(bpm<=5||original<=5||bpm>=100000||original>=100000)return 0;
 return rx3_tempo_pickup_position(bpm-5,original-5,range,current,rate,position);
}
static int rx3_tempo_fine_position(int current,int range,int direction,float *position){
 int step=rx3_tempo_step(range);if(!step||!position||(direction!=1&&direction!=-1))return 0;
 int limit=range*100;
 if(current>limit)current=limit;
 if(current<-limit)current=-limit;
 int target;
 if(direction>0)target=(current/step+(current<0&&current%step?0:1))*step;
 else target=(current/step-(current>0&&current%step?0:1))*step;
 if(target>limit)target=limit;
 if(target<-limit)target=-limit;
 /* Native conversion truncates. Aim inside the target bin, not exactly at a
  * float rounding boundary; zero and endpoints remain exact. */
 if(!target)*position=0.f;
 else if(target==limit)*position=1.f;
 else if(target==-limit)*position=-1.f;
 else *position=(target+(target>0?step*.25f:-step*.25f))/limit;
 return 1;
}
#endif
