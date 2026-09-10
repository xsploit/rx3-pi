#include <stdint.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <linux/fb.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include "drm-present.h"
#include "frame-scale.h"
#include <ft2build.h>
#include FT_FREETYPE_H
#include "pi-controls.h"
static uint32_t frame[1920*1200],chrome[1920*1200];
static uint32_t complete_frame[1280*800],candidate_frame[1280*800];
static uint32_t *published;
static unsigned accepted,rejected;
static void read_complete_frame(void){
 if(!published)return;
 for(int tries=0;tries<3;tries++){
  uint32_t before=__atomic_load_n(published+1,__ATOMIC_ACQUIRE);
  if(!before){rejected++;continue;}
  memcpy(candidate_frame,(char*)published+4096+(before&1)*sizeof(candidate_frame),sizeof(candidate_frame));
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  uint32_t after=__atomic_load_n(published+1,__ATOMIC_ACQUIRE);
  if(before==after){memcpy(complete_frame,candidate_frame,sizeof(complete_frame));accepted++;return;}
  rejected++;
 }
 /* Keep the previous complete image when the producer is busy. */
}
static FT_Face face;
static long long ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (long long)t.tv_sec*1000000000+t.tv_nsec;}
static void sleep_until(long long target){struct timespec t={target/1000000000,target%1000000000};clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&t,0);}
static void box(int x,int y,int w,int h,uint32_t c){for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)if(xx>=0&&xx<1920&&yy>=0&&yy<1200)frame[yy*1920+xx]=c;}
static void label(int cx,int cy,const char *s,int size,uint32_t c){
 FT_Set_Pixel_Sizes(face,0,size);int w=0;for(const char*p=s;*p;p++){FT_Load_Char(face,*p,FT_LOAD_RENDER);w+=face->glyph->advance.x>>6;}
 int x=cx-w/2;for(const char*p=s;*p;p++){if(FT_Load_Char(face,*p,FT_LOAD_RENDER))continue;FT_GlyphSlot g=face->glyph;
 for(unsigned y=0;y<g->bitmap.rows;y++)for(unsigned i=0;i<g->bitmap.width;i++){
 int px=x+g->bitmap_left+i,py=cy+size/3-g->bitmap_top+y;unsigned a=g->bitmap.buffer[y*g->bitmap.pitch+i];
 if(px<0||px>=1920||py<0||py>=1200||!a)continue;uint32_t old=frame[py*1920+px],v=0;
 for(int k=0;k<3;k++){unsigned shift=k*8;v|=((((c>>shift)&255)*a+((old>>shift)&255)*(255-a))/255)<<shift;}frame[py*1920+px]=v;
 }x+=g->advance.x>>6;}
}
static void drawbutton(int i,int down){int x=(i%6)*320,y=1000+(i/6)*100;box(x+4,y+4,312,92,down?0x536f84:buttons[i].color);label(x+160,y+50,buttons[i].label,26,0xffffff);}
int main(int argc,char**argv){
 if(argc<2)return 2;
 int fullscreen=argc>2&&!strcmp(argv[2],"--fullscreen");
 int src=open(argv[1],O_RDONLY),dst=open("/dev/fb0",O_RDWR);if(src<0||dst<0){perror("open");return 1;}
 struct fb_fix_screeninfo f;struct fb_var_screeninfo v;ioctl(dst,FBIOGET_FSCREENINFO,&f);ioctl(dst,FBIOGET_VSCREENINFO,&v);
 if(v.xres!=1200||v.yres!=1920||v.bits_per_pixel!=32){fprintf(stderr,"Unexpected display geometry\n");return 1;}
 uint32_t *s=mmap(0,1280*800*4,PROT_READ,MAP_SHARED,src,0);unsigned char *d=mmap(0,f.smem_len,PROT_READ|PROT_WRITE,MAP_SHARED,dst,0);if(s==MAP_FAILED||d==MAP_FAILED)return 1;
 if(argc>3&&!strcmp(argv[3],"--coherent")){
  int pf=open("/home/pompu_5/rx3-rootfs/dev/rx3-present-frame",O_RDONLY);
  if(pf<0){perror("completed-frame buffer");return 1;}
  published=mmap(0,4096+2*sizeof(complete_frame),PROT_READ,MAP_SHARED,pf,0);close(pf);
  if(published==MAP_FAILED)return 1;
  s=complete_frame;
 }
 int sf=open(UI_STATE,O_RDWR|O_CREAT,0600);if(sf<0||ftruncate(sf,sizeof(struct ui_state)))return 1;
 struct ui_state *state=mmap(0,sizeof(*state),PROT_READ|PROT_WRITE,MAP_SHARED,sf,0);if(state==MAP_FAILED)return 1;
 if(state->magic!=0x52583332){*state=(struct ui_state){0x52583332,{1,.6,0,1,.5,.5},0,1};}
 FT_Library ft;if(FT_Init_FreeType(&ft)||FT_New_Face(ft,"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",0,&face))return 1;
 box(0,0,1920,1200,0x101820);for(int i=0;i<12;i++)drawbutton(i,0);
 for(int i=0;i<6;i++){int x=i<3?0:1760,y=(i%3)*333;label(x+80,y+27,slider_names[i],23,0xffffff);}
 memcpy(chrome,frame,sizeof(frame));
 int kms=drm_start();
 fprintf(stderr,"display backend: %s\n",kms?"DRM double-buffered vsync":"fbdev fallback");
 long long deadline=ns(),report=deadline,draw_total=0,last_present=deadline;unsigned frames=0,late=0;
 for(;;){
 long long began=ns();
 read_complete_frame();
 if(!fullscreen){
 memcpy(frame,chrome,sizeof(frame));
 for(int y=0;y<1000;y++){int sy=y*4/5;for(int x=0;x<1600;x++)frame[y*1920+x+160]=s[sy*1280+x*4/5];}
 for(int i=0;i<12;i++)if(state->pressed&(1u<<i))drawbutton(i,1);
 for(int i=0;i<6;i++){int x=i<3?0:1760,y=(i%3)*333;float n=state->level[i];if(n<0)n=0;if(n>1)n=1;
 box(x+70,y+85,20,180,0x35434e);int h=(int)(180*n);box(x+70,y+265-h,20,h,0x199feb);box(x+30,y+257-h,100,16,0xeaf3fa);
 if(i==0||i==3){unsigned bit=i==0?1:2;box(x+8,y+43,144,32,state->headphone_cue&bit?0x126db0:0x35434e);label(x+80,y+60,"HP CUE",19,0xffffff);}
 char val[24];snprintf(val,sizeof(val),"%d%%",(int)(n*100+.5));label(x+80,y+305,val,25,0xd1dae2);}
 }
 if(kms){d=scanout[back].map;f.line_length=scanout[back].pitch;}
 if(fullscreen)rx3_fullscreen_present(d,f.line_length,s,frame);
 else {
 /* Tile the transpose so reads stay in cache instead of striding a whole image. */
 for(int by=0;by<1920;by+=16)for(int bx=0;bx<1200;bx+=16)
  for(int py=by;py<by+16;py++){uint32_t*row=(uint32_t*)(d+py*f.line_length);
   for(int px=bx;px<bx+16;px++)row[px]=frame[(1199-px)*1920+py];}
 }
 long long finished=ns();draw_total+=finished-began;frames++;
 if(kms){if(drm_present())return 1;long long presented=ns();if(presented-last_present>25000000)late++;last_present=presented;}else{
 deadline+=16666667;
 if(finished>deadline){late++;deadline=finished;}
 sleep_until(deadline);}
 if(frames==180){long long now=ns();fprintf(stderr,"present %.1f fps, draw %.2f ms, late %u/180\n",frames*1e9/(now-report),draw_total/180e6,late);if(published)fprintf(stderr,"complete-frame accepted %u retries %u\n",accepted,rejected);accepted=rejected=0;report=now;frames=late=0;draw_total=0;}
 }
}
