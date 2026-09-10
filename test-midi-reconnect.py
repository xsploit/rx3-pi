#!/usr/bin/env python3
"""Exercise the real parser and recovery loop with a failing ALSA transport."""
import ctypes
import errno
import importlib.util
import tempfile
from pathlib import Path
spec=importlib.util.spec_from_file_location('midi',Path(__file__).with_name('flx6-rx3.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as d:
 p=Path(d)/'map.xml';p.write_text('<root/>')
 events=[];b=m.Bridge(p,lambda *event:events.append(event),clock=lambda:0.)
 b.mapping[(0x90,0x36)]=(0x4306,1,'button')
 b.jogs[1]['delta']=12;b.jogs[1]['total']=12
 b.mapping[(0xb0,0x13)]=(0x501e,1,'msb')
 b.mapping[(0xb0,0x33)]=(0x501e,1,'lsb')
 alive=True
 class Alsa:
  opens=[];closes=0;reads=0
  def snd_rawmidi_open(self,handle,output,device,mode):
   self.opens.append(device);assert mode==2
   return 0
  def snd_rawmidi_close(self,handle):self.closes+=1
  def snd_rawmidi_read(self,handle,buf,size):
   self.reads+=1
   if self.reads==1:
    # Hold jog, seed an MSB, and leave a partial MIDI message before loss.
    data=bytes([0x90,0x36,127,0xb0,0x13,127,0x90,0x36])
    ctypes.memmove(buf,data,len(data));return len(data)
   if self.reads==2:return -errno.ENODEV
   assert not b.held and b.status is None and not b.data and not b.msb
   # New-session LSB must not reuse the previous connection's MSB.
   b.feed(bytes([0xb0,0x33,127]));assert len(events)==3
   global alive
   alive=False
   return -errno.EAGAIN
 transport=Alsa();attempts=iter([[],['hw:2,0,0'],[],['hw:3,0,0']])
 m.listen_reconnecting(b,transport,lambda:alive,lambda:next(attempts),lambda _:None)
 assert transport.opens==[b'hw:2,0,0',b'hw:3,0,0']
 assert transport.closes==2
 assert events==[(0x4306,0,1,0,0.,0),(0x4305,4,1,0,0.,3),(0x4306,2,1,0,0.,0)],events
 assert b.jogs[1]['total']==12 and b.jogs[1]['delta']==0
 # Shutdown while absent must terminate without attempting another discovery.
 alive=True
 def stop(_):
  global alive
  alive=False
 m.listen_reconnecting(b,transport,lambda:alive,lambda:[],stop)
print('PASS: absence, disconnect, release, parser reset, renumbering, shutdown')
