#include <xf86drm.h>
#include <xf86drmMode.h>
#include <drm_mode.h>
#include <poll.h>
#include <errno.h>
#include <signal.h>
static int drmfd=-1,back=0,active=0;
static uint32_t connector,crtc;
static drmModeCrtc *saved_crtc;
static drmModeModeInfo mode;
static struct {uint32_t handle,fb,pitch;uint64_t size;unsigned char *map;} scanout[2];
static void drm_cleanup(void){
 if(drmfd<0)return;
 if(active&&saved_crtc)drmModeSetCrtc(drmfd,saved_crtc->crtc_id,saved_crtc->buffer_id,saved_crtc->x,saved_crtc->y,&connector,1,&saved_crtc->mode);
 for(int i=0;i<2;i++){
  if(scanout[i].fb)drmModeRmFB(drmfd,scanout[i].fb);
  if(scanout[i].map&&scanout[i].map!=MAP_FAILED)munmap(scanout[i].map,scanout[i].size);
  if(scanout[i].handle){struct drm_mode_destroy_dumb d={.handle=scanout[i].handle};drmIoctl(drmfd,DRM_IOCTL_MODE_DESTROY_DUMB,&d);}
 }
 if(saved_crtc)drmModeFreeCrtc(saved_crtc);
 close(drmfd);drmfd=-1;
}
static void drm_stop(int sig){exit(128+sig);}
static int drm_start(void){
 drmfd=open("/dev/dri/card0",O_RDWR|O_CLOEXEC);if(drmfd<0)return 0;
 drmModeRes *r=drmModeGetResources(drmfd);if(!r)goto fail;
 for(int i=0;i<r->count_connectors;i++){
  drmModeConnector *c=drmModeGetConnector(drmfd,r->connectors[i]);
  if(c&&c->connection==DRM_MODE_CONNECTED&&c->encoder_id){
   drmModeEncoder *e=drmModeGetEncoder(drmfd,c->encoder_id);
   if(e&&e->crtc_id){saved_crtc=drmModeGetCrtc(drmfd,e->crtc_id);
    if(saved_crtc&&saved_crtc->mode_valid&&saved_crtc->mode.hdisplay==1200&&saved_crtc->mode.vdisplay==1920){connector=c->connector_id;crtc=e->crtc_id;mode=saved_crtc->mode;}
    else {if(saved_crtc)drmModeFreeCrtc(saved_crtc);saved_crtc=0;}
   }
   if(e)drmModeFreeEncoder(e);
  }
  if(c)drmModeFreeConnector(c);
  if(crtc)break;
 }
 drmModeFreeResources(r);if(!crtc)goto fail;
 for(int i=0;i<2;i++){
  struct drm_mode_create_dumb b={.width=1200,.height=1920,.bpp=32};
  if(drmIoctl(drmfd,DRM_IOCTL_MODE_CREATE_DUMB,&b))goto fail;
  scanout[i].handle=b.handle;scanout[i].pitch=b.pitch;scanout[i].size=b.size;
  if(drmModeAddFB(drmfd,1200,1920,24,32,b.pitch,b.handle,&scanout[i].fb))goto fail;
  struct drm_mode_map_dumb m={.handle=b.handle};
  if(drmIoctl(drmfd,DRM_IOCTL_MODE_MAP_DUMB,&m))goto fail;
  scanout[i].map=mmap(0,b.size,PROT_READ|PROT_WRITE,MAP_SHARED,drmfd,m.offset);
  if(scanout[i].map==MAP_FAILED)goto fail;
 }
 atexit(drm_cleanup);signal(SIGTERM,drm_stop);signal(SIGINT,drm_stop);return 1;
fail:perror("DRM setup");drm_cleanup();return 0;
}
static void flip_done(int fd,unsigned seq,unsigned sec,unsigned usec,void *data){*(int*)data=0;}
static int drm_present(void){
 if(!active){
  if(drmModeSetCrtc(drmfd,crtc,scanout[back].fb,0,0,&connector,1,&mode)){perror("DRM modeset");return -1;}
  active=1;
 }else{
  int pending=1;
  if(drmModePageFlip(drmfd,crtc,scanout[back].fb,DRM_MODE_PAGE_FLIP_EVENT,&pending)){perror("DRM page flip");return -1;}
  drmEventContext ev={.version=DRM_EVENT_CONTEXT_VERSION,.page_flip_handler=flip_done};
  while(pending){struct pollfd p={drmfd,POLLIN,0};int n=poll(&p,1,1000);
   if(n<0&&errno==EINTR)continue;
   if(n<=0||!(p.revents&POLLIN)||drmHandleEvent(drmfd,&ev)){fprintf(stderr,"DRM flip wait failed\n");return -1;}
  }
 }
 back^=1;return 0;
}
