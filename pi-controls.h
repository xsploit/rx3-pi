#ifndef PI_CONTROLS_H
#define PI_CONTROLS_H
#include <stdio.h>
#include <stdlib.h>
/* Host paths of files inside the runtime. ./rx3 start sets RX3_RUNTIME;
 * RX3_UI_STATE/RX3_UI_CONTROL or compile-time UI_STATE/UI_CONTROL override. */
static const char *runtime_path(const char *env,const char *fixed,const char *guest){
 static char paths[2][4096];static int next;
 const char *value=getenv(env);if(value&&*value)return value;
 if(fixed)return fixed;
 const char *root=getenv("RX3_RUNTIME");
 if(!root||!*root){fprintf(stderr,"RX3_RUNTIME is not set; start RX3 with ./rx3 start\n");exit(2);}
 char *path=paths[next++&1];
 if(snprintf(path,sizeof(paths[0]),"%s%s",root,guest)>=(int)sizeof(paths[0])){fprintf(stderr,"RX3_RUNTIME is too long\n");exit(2);}
 return path;
}
#ifdef UI_STATE
#define UI_STATE_FIXED UI_STATE
#else
#define UI_STATE_FIXED 0
#endif
#ifdef UI_CONTROL
#define UI_CONTROL_FIXED UI_CONTROL
#else
#define UI_CONTROL_FIXED 0
#endif
#define ui_state_path() runtime_path("RX3_UI_STATE",UI_STATE_FIXED,"/dev/rx3-ui-state")
#define ui_control_path() runtime_path("RX3_UI_CONTROL",UI_CONTROL_FIXED,"/dev/rx3-control")
#define CONTENT_X 160
#define CONTENT_W 1600
#define CONTENT_H 1000
struct command {int key,operation,channel,value;float analog;int extra;};
struct ui_state {unsigned magic;float level[6];unsigned pressed;unsigned headphone_cue;};
struct button {const char *label;int key,channel,scroll;unsigned color;};
static const struct button buttons[12]={
 {"USB 1",0x209,0,0,0x08699c},{"BROWSE",0x202,0,0,0x08699c},
 {"BACK",0x420d,0,0,0x283542},{"UP",0x420c,0,-1,0x283542},
 {"DOWN",0x420c,0,1,0x283542},{"ENTER",0x420c,0,0,0x283542},
 {"LOAD 1",0x4311,1,0,0x08699c},{"CUE 1",0x4102,1,0,0x836315},
 {"PLAY / PAUSE 1",0x4101,1,0,0x12623a},{"LOAD 2",0x4311,2,0,0x08699c},
 {"CUE 2",0x4102,2,0,0x836315},{"PLAY / PAUSE 2",0x4101,2,0,0x12623a}
};
static const char *slider_names[6]={"DECK 1","MASTER","HP MIX","DECK 2","HP LEVEL","CROSS"};
static const int slider_keys[6]={0x501e,0x4403,0x4405,0x501e,0x4406,0x6017};
static const int slider_channels[6]={1,0,0,2,0,0};
#endif
