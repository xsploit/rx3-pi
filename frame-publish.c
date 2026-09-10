/* Publish a stable framebuffer after the RX3 layer compositor returns. */
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
extern char *program_invocation_short_name;
#define PIXELS (1280*800*4)
#define MAGIC 0x52583346u
static uint32_t *exchange;
static void *source;
static int (*original_update)(int);
static int update(int layer){
 int result=original_update(layer);
 if(layer==0&&exchange){
  uint32_t seq=__atomic_load_n(exchange+1,__ATOMIC_RELAXED);
  memcpy((char*)exchange+4096+((seq+1)&1)*PIXELS,source,PIXELS);
  __atomic_store_n(exchange+1,seq+1,__ATOMIC_RELEASE);
 }
 return result;
}
__attribute__((constructor))static void install_frame_publisher(void){
 if(!program_invocation_short_name||strcmp(program_invocation_short_name,"rbp-pi"))return;
 uint32_t *entry=(void*)0x1a6528;
 if(entry[0]!=0xe92d4ff0||entry[1]!=0xe3a080a4)return;
 int in=open("/dev/fb0",O_RDONLY),out=open("/dev/rx3-present-frame",O_RDWR|O_CREAT,0600);
 if(in<0||out<0)return;
 if(ftruncate(out,4096+2*PIXELS))return;
 source=mmap(0,PIXELS,PROT_READ,MAP_SHARED,in,0);
 exchange=mmap(0,4096+2*PIXELS,PROT_READ|PROT_WRITE,MAP_SHARED,out,0);
 close(in);close(out);
 if(source==MAP_FAILED||exchange==MAP_FAILED){exchange=0;return;}
 exchange[0]=0;exchange[1]=0;exchange[2]=getpid();
 __atomic_store_n(exchange,MAGIC,__ATOMIC_RELEASE);
 long page=getpagesize();uint32_t *tr=mmap(0,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
 if(tr==MAP_FAILED)return;
 tr[0]=entry[0];tr[1]=entry[1];tr[2]=0xe51ff004;tr[3]=0x1a6530;
 if(mprotect(tr,page,PROT_READ|PROT_EXEC))return;
 syscall(0xf0002,tr,tr+4,0);original_update=(void*)tr;
 void *base=(void*)((uintptr_t)entry&~((uintptr_t)page-1));
 if(mprotect(base,page,PROT_READ|PROT_WRITE|PROT_EXEC))return;
 entry[0]=0xe51ff004;entry[1]=(uintptr_t)update;
 syscall(0xf0002,entry,entry+2,0);mprotect(base,page,PROT_READ|PROT_EXEC);
 write(2,"completed-frame publisher installed\n",36);
}
