#ifndef RX3_TEMPO_INPUT_H
#define RX3_TEMPO_INPUT_H
#define RX3_MIDI_TEMPO_TAG 0x544d
struct rx3_tempo_input {float target,previous;int touched,have_previous,midi_owned;};
/* Speed direction, independent of a controller's physical fader orientation. */
static int rx3_tempo_input_hint(const struct rx3_tempo_input *s){
 if(!s->touched||s->midi_owned)return 0;
 if(!s->have_previous)return 3;
 float d=s->target-s->previous;
 return d>2.f/8192?1:(d<-2.f/8192?2:0);
}
static int rx3_tempo_input_accept(struct rx3_tempo_input *s,float value,int midi){
 if(!(value>=-1.f&&value<=1.f))return 0;
 if(!midi){s->target=value;s->touched=1;s->midi_owned=0;return 1;}
 /* Match within two 14-bit MIDI increments, or cross the touch target. */
 float distance=value-s->target;
 int crossed=s->have_previous&&((s->previous<s->target&&value>=s->target)||(s->previous>s->target&&value<=s->target));
 int accept=!s->touched||s->midi_owned||(distance>=-2.f/8192&&distance<=2.f/8192)||crossed;
 s->previous=value;s->have_previous=1;
 if(accept){s->target=value;s->midi_owned=1;}
 return accept;
}
#endif
