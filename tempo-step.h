#ifndef RX3_TEMPO_STEP_H
#define RX3_TEMPO_STEP_H
/* RX3 v1.19 Tempo::STEP_TBL_: percentage hundredths per native step. */
static int rx3_tempo_step(int range){return range==6?2:(range==10||range==16?5:(range==100?50:0));}
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
