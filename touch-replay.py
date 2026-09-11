#!/usr/bin/env python3
"""Replay a landscape touch through the same Linux-input bridge as the panel.
Usage: RX3_RUNTIME=/path/to/runtime touch-replay.py X Y (uses build/rx3-touch-bridge)."""
import os,subprocess,struct,time,sys
root=os.environ.get('RX3_RUNTIME')
if not root or len(sys.argv)!=3:sys.exit(__doc__)
x,y=map(int,sys.argv[1:3])
bridge=os.path.join(os.path.dirname(os.path.realpath(__file__)),'build','rx3-touch-bridge')
p=subprocess.Popen([bridge,'--replay',root+'/dev/tsc2007_2-0048','--fullscreen'],stdin=subprocess.PIPE)
def event(t,c,v):
 p.stdin.write(struct.pack('llHHi',0,0,t,c,v));p.stdin.flush()
event(3,47,0);event(3,57,100);event(3,53,1199-y);event(3,54,x);event(0,0,0)
time.sleep(.22)
event(3,57,-1);event(0,0,0);time.sleep(.25)
p.stdin.close();p.wait()
