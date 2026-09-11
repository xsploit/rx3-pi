#include <asm/ioctl.h>
#include <linux/fb.h>
#include <stdarg.h>
#include <errno.h>
static unsigned yoffset;
static void clear(void *p,unsigned n){unsigned char *q=p;while(n--)*q++=0;}
int ioctl(int fd,unsigned long request,...){
 va_list ap;va_start(ap,request);void *arg=va_arg(ap,void*);va_end(ap);
 if(((request>>8)&255)==0x70){if((request&0x80000000)&&arg){unsigned n=(request>>16)&0x3fff;if(n<=64)clear(arg,n);}return 0;}
 if(request==0x80046b00){*(unsigned*)arg=3;return 0;}
 if(request==0x80026b01){*(unsigned*)arg=3900;return 0;}
 if(request==0x40046b00||request==0x40026b01)return 0;
 if(request==FBIOGET_FSCREENINFO){struct fb_fix_screeninfo *f=arg;clear(f,sizeof(*f));f->id[0]='R';f->id[1]='X';f->id[2]='3';f->smem_len=1280*800*4;f->type=FB_TYPE_PACKED_PIXELS;f->visual=FB_VISUAL_TRUECOLOR;f->line_length=1280*4;return 0;}
 if(request==FBIOGET_VSCREENINFO){struct fb_var_screeninfo *v=arg;clear(v,sizeof(*v));v->xres=v->xres_virtual=1280;v->yres=v->yres_virtual=800;v->bits_per_pixel=32;v->red.offset=16;v->red.length=8;v->green.offset=8;v->green.length=8;v->blue.length=8;v->height=135;v->width=216;v->pixclock=20000;v->left_margin=40;v->right_margin=40;v->upper_margin=10;v->lower_margin=10;v->hsync_len=20;v->vsync_len=3;return 0;}
 if(request==FBIOPUT_VSCREENINFO){struct fb_var_screeninfo *v=arg;if(v->bits_per_pixel!=32){errno=EINVAL;return -1;}return 0;}
 if(request==FBIOPAN_DISPLAY||request==FBIOPUTCMAP||request==FBIOGETCMAP||request==FBIOBLANK||request==FBIO_WAITFORVSYNC)return 0;
 register long r0 asm("r0")=fd;register long r1 asm("r1")=request;register void *r2 asm("r2")=arg;register long r7 asm("r7")=54;
 asm volatile("svc 0":"+r"(r0):"r"(r1),"r"(r2),"r"(r7):"memory");
 if(r0<0 && r0>=-4095){errno=-r0;return -1;}return r0;
}
extern void *dlsym(void*,const char*);
extern void *dlvsym(void*,const char*,const char*);
extern int write(int,const void*,unsigned);
static void logtext(const char *s){unsigned n=0;while(s[n])n++;write(2,s,n);}
static int logresult(const char *s,int v){char h[12]=" 00000000\n";unsigned u=v;for(int i=8;i>0;i--){h[i]="0123456789abcdef"[u&15];u>>=4;}logtext(s);write(2,h,10);return v;}
void *dlopen(const char *name,int flags){static void *(*real)(const char*,int);if(!real)real=dlsym((void*)-1,"dlopen");return real(name,flags&~8);}
#ifndef RX3_AUDIO_RECOVERY
int snd_pcm_open(void **pcm,const char *name,int stream,int mode){
 static int (*real)(void**,const char*,int,int);if(!real)real=dlsym((void*)-1,"snd_pcm_open");
 unsigned n=0;while(name[n])n++;const char *target=stream?"null":(n&&name[n-1]=='0'?"rx3out":(n&&name[n-1]=='1'?"rx3cue":"null"));
 logtext("PCM open ");logtext(name);return logresult(stream?" capture":" playback",real(pcm,target,stream,mode));
}
#define WRAP2(name) int name(void*a,void*b){static int(*real)(void*,void*);if(!real)real=dlsym((void*)-1,#name);return logresult(#name,real(a,b));}
#define WRAP3(name) int name(void*a,void*b,int c){static int(*real)(void*,void*,int);if(!real)real=dlsym((void*)-1,#name);int v=real(a,b,c);logresult(#name " value",c);return logresult(#name,v);}
WRAP2(snd_pcm_hw_params)
WRAP2(snd_pcm_hw_params_any)
int snd_pcm_hw_params_set_access(void*a,void*b,int c){static int(*real)(void*,void*,int);if(!real)real=dlsym((void*)-1,"snd_pcm_hw_params_set_access");return logresult("interleaved access",real(a,b,c==4?3:c));}
WRAP3(snd_pcm_hw_params_set_format)
WRAP3(snd_pcm_hw_params_set_channels)
#endif
/* build.sh sets the card from rx3.conf [audio] card; DDJFLX6 is the tested one. */
#ifndef RX3_CTL_DEVICE
#define RX3_CTL_DEVICE "hw:CARD=DDJFLX6"
#endif
int snd_ctl_open(void **ctl,const char *name,int mode){static int(*real)(void**,const char*,int);if(!real)real=dlsym((void*)-1,"snd_ctl_open");return logresult("CTL open",real(ctl,RX3_CTL_DEVICE,mode));}
int snd_pcm_hw_params_get_channels_max(const void *p,unsigned *v){static int(*real)(const void*,unsigned*);if(!real)real=dlvsym((void*)-1,"snd_pcm_hw_params_get_channels_max","ALSA_0.9.0rc4");int r=real(p,v);if(r>=0&&*v>2)*v=2;logresult("channels max",*v);return logresult("channels max result",r);}
int snd_ctl_pcm_info(void *ctl,void *info){
 static int(*real)(void*,void*);static int(*stream)(const void*);
 if(!real)real=dlsym((void*)-1,"snd_ctl_pcm_info");
 if(!stream)stream=dlsym((void*)-1,"snd_pcm_info_get_stream");
 if(stream(info)==1)return 0; /* Virtual silent capture, exposed by the null PCM. */
 return real(ctl,info);
}
