#ifndef RX3_NATIVE_ZOOM_LAYOUT_H
#define RX3_NATIVE_ZOOM_LAYOUT_H
enum { RX3_ZOOM_X=1090, RX3_ZOOM_Y=354, RX3_ZOOM_W=180, RX3_ZOOM_H=28 };
static inline int rx3_zoom_direction_at(int x,int y){
 if(y<RX3_ZOOM_Y||y>=RX3_ZOOM_Y+RX3_ZOOM_H)return 0;
 x-=RX3_ZOOM_X;
 if(x>=0&&x<88)return -1;
 if(x>=92&&x<RX3_ZOOM_W)return 1;
 return 0;
}
#endif
