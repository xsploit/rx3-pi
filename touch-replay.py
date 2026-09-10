#!/usr/bin/env python3
"""Replay a landscape touch through the same Linux-input bridge as the panel."""
import subprocess,struct,time,sys
x,y=map(int,sys.argv[1:3])
p=subprocess.Popen(['/home/pompu_5/rx3-touch-bridge','--replay','/home/pompu_5/rx3-rootfs/dev/tsc2007_2-0048','--fullscreen'],stdin=subprocess.PIPE)
def event(t,c,v):
 p.stdin.write(struct.pack('llHHi',0,0,t,c,v));p.stdin.flush()
event(3,47,0);event(3,57,100);event(3,53,1199-y);event(3,54,x);event(0,0,0)
time.sleep(.22)
event(3,57,-1);event(0,0,0);time.sleep(.25)
p.stdin.close();p.wait()
