#include <assert.h>
#include <math.h>
#include "tempo-input.h"
int main(void){
 struct rx3_tempo_input a={0},b={0};
 assert(rx3_tempo_input_accept(&a,0,1));
 assert(rx3_tempo_input_accept(&a,.505f,0));
 assert(!rx3_tempo_input_accept(&a,.01f,1));
 assert(!rx3_tempo_input_accept(&a,.49f,1));
 assert(a.target==.505f);
 assert(rx3_tempo_input_accept(&a,.51f,1));
 assert(rx3_tempo_input_accept(&a,0,1));
 assert(rx3_tempo_input_accept(&a,-.49f,0));
 assert(!rx3_tempo_input_accept(&a,-.01f,1));
 assert(rx3_tempo_input_accept(&a,-.5f,1));
 assert(rx3_tempo_input_accept(&a,.001f,0));
 assert(!rx3_tempo_input_accept(&a,-.5f,1));
 assert(rx3_tempo_input_accept(&a,.0011f,1));
 assert(rx3_tempo_input_accept(&b,.8f,1));
 assert(!rx3_tempo_input_accept(&a,NAN,1));
 assert(!rx3_tempo_input_accept(&a,INFINITY,0));
 assert(!rx3_tempo_input_accept(&a,1.01f,0));
 /* Unknown hardware position after a touch must not seize control. */
 b=(struct rx3_tempo_input){0};
 assert(rx3_tempo_input_accept(&b,.5f,0));
 assert(!rx3_tempo_input_accept(&b,-.5f,1));
 assert(rx3_tempo_input_accept(&b,.5f,1));
}
