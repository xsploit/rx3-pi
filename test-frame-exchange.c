/* Exercise the actual presenter reader against a separate racing writer. */
#define main presenter_main
#include "fb-present.c"
#undef main
#include <sys/wait.h>
int main(void){
 size_t bytes=4096+2*sizeof(complete_frame);
 published=mmap(0,bytes,PROT_READ|PROT_WRITE,MAP_SHARED|MAP_ANONYMOUS,-1,0);
 if(published==MAP_FAILED)return 2;
 pid_t child=fork();if(child<0)return 2;
 if(!child){
  for(uint32_t seq=1;seq<=500;seq++){
   uint32_t *dst=(void*)((char*)published+4096+(seq&1)*sizeof(complete_frame));
   for(unsigned i=0;i<1280*800;i++)dst[i]=seq;
   __atomic_store_n(published+1,seq,__ATOMIC_RELEASE);
  }
  __atomic_store_n(published+3,1,__ATOMIC_RELEASE);_exit(0);
 }
 unsigned checked=0;
 do{
  unsigned previous=accepted;read_complete_frame();
  if(accepted!=previous){
   uint32_t generation=complete_frame[0];
   for(unsigned i=0;i<1280*800;i++)if(complete_frame[i]!=generation){fprintf(stderr,"mixed frame at pixel %u\n",i);return 1;}
   if(!generation||generation>500)return 1;checked++;
  }
 }while(!__atomic_load_n(published+3,__ATOMIC_ACQUIRE));
 int status;waitpid(child,&status,0);
 /* A fast writer may make every concurrent read retry. That is valid:
  * verify the entire final frame once the producer is quiescent. */
 read_complete_frame();
 for(unsigned i=0;i<1280*800;i++)if(complete_frame[i]!=500){fprintf(stderr,"invalid final frame at pixel %u\n",i);return 1;}
 printf("Validated %u accepted frames with %u retries; final generation 500\n",checked,rejected);
 return WIFEXITED(status)&&WEXITSTATUS(status)==0?0:1;
}
