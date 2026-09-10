#ifndef PI_CONTROLS_H
#define PI_CONTROLS_H
#define UI_STATE "/home/pompu_5/rx3-rootfs/dev/rx3-ui-state"
#define UI_CONTROL "/home/pompu_5/rx3-rootfs/dev/rx3-control"
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
