#define _POSIX_C_SOURCE 200809L
#include "audio-pacer.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <time.h>
static uint64_t now_ns(void){
 struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));
 return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;
}
static void until(uint64_t ns){
 struct timespec t={(time_t)(ns/1000000000),(long)(ns%1000000000)};
 int e;do {e=clock_nanosleep(CLOCK_MONOTONIC,TIMER_ABSTIME,&t,0);}while(e==EINTR);
 assert(!e);
}
int main(void){
 struct rx3_audio_pacer p={0};assert(!rx3_audio_pacer_init(&p,44100,128));
 uint64_t start=now_ns();
 for(int i=0;i<441;i++)for(int output=0;output<2;output++){
  uint64_t deadline=rx3_audio_pacer_deadline(&p,output,now_ns());
  until(deadline);
 }
 uint64_t elapsed=now_ns()-start;
 printf("Offline pair pacing: %.3f ms wall time for 1280 ms of engine blocks\n",elapsed/1000000.0);
 fflush(stdout);
 assert(elapsed>=1280000000&&elapsed<1530000000);
}
