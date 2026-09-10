#!/usr/bin/env python3
"""Check the installed-script nudge quantum, reversal residuals and reset."""
import importlib.util,tempfile
from pathlib import Path
s=importlib.util.spec_from_file_location('b',Path(__file__).with_name('flx6-rx3.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.NamedTemporaryFile(mode='w') as f:
 f.write('<root/>');f.flush();events=[];b=m.Bridge(f.name,lambda *v:events.append(v))
 for ch in (1,2):
  for _ in range(15):b.grid_jog(ch,65)
  assert not events
  b.grid_jog(ch,65);assert events.pop()==(0,4,ch,20,0.,0x4744)
  for _ in range(16):b.grid_jog(ch,63)
  assert events.pop()==(0,4,ch,-20,0.,0x4744)
  b.grid_jog(ch,79);b.grid_jog(ch,49);assert not events and b.grid_ticks[ch]==0
  b.grid_jog(ch,127);assert events.pop()==(0,4,ch,60,0.,0x4744)
  assert b.grid_ticks[ch]==15
  b.release();assert b.grid_ticks[ch]==0
 # Ordinary shifted packets and the controller's dedicated shifted address.
 b.mapping[(0x90,0x3f)]=(0x4103,1,'shift')
 b.mapping[(0xb0,0x21)]=(0x4305,1,'jog')
 b.mapping[(0xb0,0x29)]=(0,1,'grid-jog')
 b.feed([0x90,0x3f,127]);events.clear()
 b.feed([0xb0,0x21,72,0x29,72]);assert events==[(0,4,1,20,0.,0x4744)]
 b.feed([0xb0,0x29,79]);b.feed([0x90,0x3f,0]);assert b.grid_ticks[1]==0
print('PASS: 16 ticks per signed nudge, residual reversal, per-deck reset and shifted MIDI paths')
