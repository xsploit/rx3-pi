/* RX3 v1.19 input adapter: use the firmware's message-queued key entry. */
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <string.h>
extern char *program_invocation_short_name;
extern int pthread_create(unsigned long*,const void*,void *(*)(void*),void*);
struct command {int key,operation,channel,value;float analog;int extra;};
/* Main deck-information panel (native window key136) exists before loading
 * a track too. Its visibility distinguishes the player from Browse. */
static int main_panel_visible(void){
 void *active=*(void *volatile *)(0x024942bc+0x20);
 if(!active||*(volatile int16_t*)((char*)active+6)!=0)return 0;
 uintptr_t p=*(volatile uint32_t*)0x0245b880;
 for(int i=0;p&&i<256;i++,p=*(volatile uint32_t*)(p+0x84)){
  if(*(volatile uint32_t*)(p+0xc)==136)return (*(volatile uint32_t*)(p+4)&8)!=0;
 }
 return 0;
}
static void *control_thread(void *unused){
 sleep(3);
 int fd=open("/dev/rx3-control",O_RDWR);
 if(fd<0)return 0;
 void *manager=0;
 while(!manager){void *root=*(void *volatile *)0x026867c0;if(root)manager=*(void **)((char*)root+0x64);if(!manager)sleep(1);}
 /* The two physical panel CPUs normally release this startup input gate. */
 ((void (*)(void*,int))0x37c8d8)(manager,3);
 void (*sendkey)(void*,int,int,int,long,float,long)=(void*)0x37ad64;
 for(int ch=1;ch<=2;ch++){
  const int keys[]={0x5019,0x501a,0x501b,0x501c,0x509d,0x501e};
  for(int i=0;i<6;i++)sendkey(manager,keys[i],4,ch,0,i==5?1.f:.5f,0);
 }
 sendkey(manager,0x6017,4,0,0,.5f,0);
 sendkey(manager,0x4403,4,0,0,.6f,0);
 sendkey(manager,0x4406,4,0,0,.5f,0);
 sendkey(manager,0x4405,4,0,0,0.f,0);
 sendkey(manager,0x5020,0,1,0,0.f,0);
 sendkey(manager,0x5020,2,1,0,0.f,0);
 const char *(*keyname)(void*)=(void*)0x37cde4;
 int names=open("/tmp/rx3-keycodes.txt",O_WRONLY|O_CREAT|O_TRUNC,0644);
 if(names>=0){
  uint32_t key[16]={0};const char *last=0;
  for(unsigned i=0;i<0x9000;i++){
   key[2]=i;const char *name=keyname(key);
   if(name&&name!=last){char hex[6];for(int j=0;j<4;j++)hex[j]="0123456789abcdef"[(i>>(12-j*4))&15];hex[4]=' ';hex[5]=0;write(names,hex,5);write(names,name,strlen(name));write(names,"\n",1);last=name;}
  }
  close(names);
 }
 const char ready[]="RX3 control adapter ready\n";write(2,ready,sizeof(ready)-1);
 struct command c;unsigned have=0;
 for(;;){int n=read(fd,(char*)&c+have,sizeof(c)-have);if(n<=0){sleep(1);continue;}have+=n;if(have<sizeof(c))continue;have=0;
  if(c.key<0||c.key>65535||c.operation<0||c.operation>15||c.channel<0||c.channel>2)continue;
  /* BiteDJ VIEW opens Browse; BACK opens Browse or steps up in it.
   * Consume release in the bridge and emit paired native key events here. */
  if(c.operation==0&&(c.extra==0x4256||c.extra==0x424b)){
   if(main_panel_visible()){
    sendkey(manager,0x202,0,0,0,0.f,0);
    sendkey(manager,0x202,2,0,0,0.f,0);
   }else if(c.extra==0x424b){
    sendkey(manager,0x420d,0,0,0,0.f,0);
    sendkey(manager,0x420d,2,0,0,0.f,0);
   }
   continue;
  }
  /* FLX6 browse encoder: enter the browser before forwarding rotation.
   * The native main-screen rotary normally adjusts waveform zoom. */
  if(c.key==0x420c&&c.operation==4&&c.extra==0x4252){
   if(main_panel_visible()){
    void *active=*(void *volatile *)(0x024942bc+0x20);
    if(!active||*(volatile int16_t*)((char*)active+6)!=0)continue;
    sendkey(manager,0x202,0,0,0,0.f,0);
    sendkey(manager,0x202,2,0,0,0.f,0);
    for(int tries=0;tries<100&&main_panel_visible();tries++)usleep(10000);
    if(main_panel_visible())continue;
    usleep(50000);
   }
   c.extra=0;
  }
  sendkey(manager,c.key,c.operation,c.channel,c.value,c.analog,c.extra);
 }
 return 0;
}
__attribute__((constructor))static void start_control(void){
 if(!program_invocation_short_name||strcmp(program_invocation_short_name,"rbp-pi"))return;
 unsigned long thread;pthread_create(&thread,0,control_thread,0);
}
