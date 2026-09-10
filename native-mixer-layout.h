#ifndef RX3_NATIVE_MIXER_LAYOUT_H
#define RX3_NATIVE_MIXER_LAYOUT_H
/* Native screen coordinates: panel starts at y44. */
static inline int mixer_column_center(int index){
 if(index==6)return 533;
 if(index==8)return 640;
 if(index==9)return 747;
 if(index==16)return (6*480+240)/7;
 if(index==17)return 800+(6*480+240)/7;
 if(index<6)return (index*480+240)/7;
 return 800+((index-10)*480+240)/7;
}
static inline int mixer_slider_at(int x,int y){
 if(x<0||x>=1280)return -1;
 if(y>=628&&y<=678&&x>=48&&x<=1232)return 7;
 if(y<184||y>614)return -1;
 if(x>=480&&x<800){static const int ids[3]={6,8,9};return ids[(x-480)*3/320];}
 if(x<480){int col=x*7/480;return col==6?16:col;}
 int col=(x-800)*7/480;return col==6?17:col+10;
}
static inline float mixer_slider_value(int index,int x,int y){
 if(index>=16&&y>=397&&y<=401)return .5f; /* Neutral detent tolerates touch calibration rounding. */
 float value=index==7?(x-80)/1120.f:(594-y)/390.f;
 if(index>=16){if(value<=.01f)return 0;if(value>=.99f)return 1;}
 return value<0?0:(value>1?1:value);
}
#endif
