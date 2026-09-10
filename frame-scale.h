#ifndef RX3_FRAME_SCALE_H
#define RX3_FRAME_SCALE_H
#include <stdint.h>
#include <string.h>
/* Pixel-exact equivalent of 1280x800 -> nearest 1920x1200 -> rotate.
 * Rotate at native size, then write complete scanout rows. The reversed X
 * axis uses ceil(2*x/3), preserving the old scaler's orientation and phase. */
static void rx3_fullscreen_present(unsigned char *dst,unsigned pitch,
 const uint32_t *src,uint32_t *rotated){
 for(int by=0;by<1280;by+=16)for(int bx=0;bx<800;bx+=16)
  for(int y=by;y<by+16;y++)for(int x=bx;x<bx+16;x++)
   rotated[y*800+x]=src[(799-x)*1280+y];
 uint32_t row[1200];int previous=-1;
 for(int y=0;y<1920;y++){
  int sy=y*2/3;
  if(sy!=previous){
   const uint32_t *in=rotated+sy*800;
   for(int x=0;x<1200;x+=3){int sx=x*2/3;row[x]=in[sx];row[x+1]=row[x+2]=in[sx+1];}
   previous=sy;
  }
  memcpy(dst+y*pitch,row,sizeof(row));
 }
}
#endif
