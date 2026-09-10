#!/usr/bin/env python3
"""BiteDJ shift/scratch overlap: cancel, suppress, isolate, and recover."""
import importlib.util,tempfile
from pathlib import Path
s=importlib.util.spec_from_file_location('bridge',Path(__file__).with_name('flx6-rx3.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
controls=[]
for deck in (1,2):
 for key,status,note in (('shiftPressed',0x8f+deck,0x3f),('jogTouch',0x8f+deck,0x36),('jogTurn',0xaf+deck,0x21)):
  controls.append(f'<control><group>[Channel{deck}]</group><key>PioneerDDJFLX6.{key}</key><status>{status}</status><midino>{note}</midino></control>')
with tempfile.NamedTemporaryFile(mode='w') as f:
 f.write('<root><controls>'+''.join(controls)+'</controls></root>');f.flush()
 for deck in (1,2):
  events=[];clock=[0.];b=m.Bridge(f.name,lambda *e:events.append(e),lambda:clock[0])
  def msg(note,value):b.feed(bytes([0x8f+deck,note,value]))
  def jog(d=deck):
   b.feed(bytes([0xaf+d,0x21,74]));clock[0]+=.02;b.tick()
  msg(0x36,127);jog();assert b.jogs[deck]['speed']>0
  msg(0x3f,127)
  assert events[-3][0:4]==(0x4305,4,deck,0)
  assert events[-2]==(0x4306,2,deck,0,0.,0)
  assert events[-1]==(0x4103,0,deck,0,0.,0)
  assert (0x4306,deck) not in b.held
  n=len(events);total=b.jogs[deck]['total']
  msg(0x36,0);msg(0x36,127);jog();assert len(events)==n and b.jogs[deck]['total']==total
  jog(3-deck);assert events[-1][2]==3-deck and events[-1][4]>0
  msg(0x3f,0);msg(0x36,127);assert events[-1]==(0x4306,0,deck,0,0.,0)
  msg(0x3f,127);b.release();assert not any(b.shift.values()) and not b.held
  msg(0x36,127);assert events[-1]==(0x4306,0,deck,0,0.,0)
print('PASS: both decks cancel scratch on Shift, suppress shifted jog, isolate other deck, resume and reset')
