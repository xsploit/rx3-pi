#include <assert.h>
#include "native-mixer-layout.h"
int main(void){
 for(int i=0;i<18;i++)if(i!=7){int x=mixer_column_center(i);assert(mixer_slider_at(x,399)==i);assert(mixer_slider_value(i,x,399)==.5f);}
 for(int x=0;x<1280;x++){int i=mixer_slider_at(x,399);assert(i>=0&&i<18&&i!=7);}
 assert(mixer_slider_at(80,652)==7);assert(mixer_slider_at(1200,652)==7);
 assert(mixer_slider_value(7,48,652)==0);assert(mixer_slider_value(7,1232,652)==1);assert(mixer_slider_value(7,640,652)==.5f);
 for(int i=16;i<18;i++){for(int y=397;y<=401;y++)assert(mixer_slider_value(i,0,y)==.5f);assert(mixer_slider_value(i,0,592)==0);assert(mixer_slider_value(i,0,206)==1);}
 assert(mixer_slider_at(640,620)==-1);assert(mixer_slider_at(640,690)==-1);assert(mixer_slider_at(-1,652)==-1);
}
