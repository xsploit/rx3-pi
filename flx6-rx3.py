#!/usr/bin/env python3
"""Use BiteDJ's installed MIDI definitions to feed the RX3 native key queue.
Input only; pad-mode switching and LED feedback remain pending.
"""
import argparse, ctypes, errno, json, os, re, signal, struct, subprocess, time
import xml.etree.ElementTree as ET
BUTTONS={'play':0x4101,'cue_default':0x4102,'loop_in':0x410c,'loop_out':0x410d,
 'reloop_toggle':0x410e,'slip_enabled':0x4110,'sync_enabled':0x4112,'sync_leader':0x4111,
 'keylock':0x4108,'quantize':0x410b,'pfl':0x5020,'LoadSelectedTrack':0x4311,
 'MoveFocusForward':0x420c,'MoveFocusBackward':0x420d,'PioneerDDJFLX6.shiftPressed':0x4103}
ANALOG={'pregain':0x5019,'parameter3':0x501a,'parameter2':0x501b,'parameter1':0x501c,
 'volume':0x501e,'super1':0x509d,'crossfader':0x6017,'headMix':0x4405}
class Bridge:
 def __init__(self,xml,emit,clock=time.monotonic):
  self.clock=clock;self.jogs={ch:dict(total=0,delta=0,last=clock(),moved=0,speed=0) for ch in (1,2)}
  self.emit=emit;self.mapping={};self.msb={};self.held=set();self.status=None;self.data=[]
  for c in ET.parse(xml).findall('.//controls/control'):
   g=c.findtext('group','');key=c.findtext('key','');match=re.search(r'\[Channel(\d)\]',g)
   if match:
    channel=int(match[1])
    if channel>2:continue
   elif g in ('[Master]','[Library]','[Tab]'):channel=0
   else:continue
   mode='button';native=BUTTONS.get(key)
   if g=='[Tab]' and key in ('library','PioneerDDJFLX6.viewPressed'):native=0x202;mode='view'
   if key=='PioneerDDJFLX6.backPressed':native=0x420d;mode='back'
   if key in ANALOG:native=ANALOG[key];mode='analog'
   if key=='PioneerDDJFLX6.jogTurn':native=0x4305;mode='jog'
   if key=='PioneerDDJFLX6.jogTouch' and int(c.findtext('midino'),0)==0x36:native=0x4306
   if key=='PioneerDDJFLX6.tempoSliderMSB':native=0x4109;mode='tempo-msb'
   if key=='PioneerDDJFLX6.tempoSliderLSB':native=0x4109;mode='tempo-lsb'
   if key=='PioneerDDJFLX6.browseRotate':native=0x420c;mode='relative'
   pad=re.fullmatch(r'hotcue_([1-8])_activate',key)
   if pad:native=0x4116+int(pad[1])
   if native is None:continue
   opts={o.tag for o in c.findall('./options/*')}
   if 'fourteen-bit-msb' in opts:mode='msb'
   if 'fourteen-bit-lsb' in opts:mode='lsb'
   addr=(int(c.findtext('status'),0),int(c.findtext('midino'),0))
   item=(native,channel,mode)
   if addr in self.mapping and self.mapping[addr]!=item:raise ValueError(f'Conflicting mapping {addr}')
   self.mapping[addr]=item
 def message(self,status,note,value):
  off=status&0xf0==0x80
  if off:status+=0x10;value=0
  item=self.mapping.get((status,note))
  if not item:return
  key,ch,mode=item
  if mode in ('view','back'):
   if value:self.emit(key,0,ch,0,0.,0x4256 if mode=='view' else 0x424b)
  elif mode=='jog':
   j=self.jogs[ch];delta=value-64
   if delta:j['delta']+=delta;j['total']+=delta;j['moved']=self.clock()
  elif mode=='button':
   op=0 if value else 2
   if key==0x4306 and op==2:self.stop_jog(ch)
   if op==0:self.held.add((key,ch))
   else:self.held.discard((key,ch))
   self.emit(key,op,ch,0,0.,0)
  elif mode=='relative':
   delta=value if value<64 else value-128
   if delta:self.emit(key,4,ch,delta,0.,0x4252) # browser-only encoder intent
  elif mode in ('msb','tempo-msb'):self.msb[(status,note)]=value
  elif mode=='tempo-lsb':
   hi=self.msb.get((status,note-32))
   if hi is not None:self.emit(key,5,ch,0,((hi<<7)|value)/8192.-1.,0)
  elif mode=='lsb':
   hi=self.msb.get((status,note-32))
   if hi is not None:self.emit(key,4,ch,0,((hi<<7)|value)/16383.,0)
  else:self.emit(key,4,ch,0,value/127.,0)
 def feed(self,data):
  for b in data:
   if b>=0xf8:continue
   if b&0x80:
    self.data=[];self.status=b if b<0xf0 else None
   elif self.status is not None:
    self.data.append(b)
    n=1 if self.status&0xf0 in (0xc0,0xd0) else 2
    if len(self.data)==n:
     if n==2:self.message(self.status,*self.data)
     self.data=[]
 def pulse(self,ch):
  # RX3 hardware uses 1620 pulses/revolution; BiteDJ FLX6 uses 7200.
  return round(self.jogs[ch]['total']*1620/7200)&65535
 def stop_jog(self,ch):
  j=self.jogs[ch];self.emit(0x4305,4,ch,0,0.,self.pulse(ch));j['delta']=0;j['speed']=0;j['last']=self.clock()
 def tick(self):
  now=self.clock()
  for ch,j in self.jogs.items():
   elapsed=now-j['last']
   if elapsed<.01:continue
   if j['delta']:
    # 1x = 33 1/3 RPM = one revolution/1.8 seconds.
    speed=j['delta']*1.8/(7200*elapsed)
    self.emit(0x4305,4,ch,0,speed,self.pulse(ch))
    j['delta']=0;j['speed']=speed;j['last']=now
   elif j['speed'] and now-j['moved']>=.04:self.stop_jog(ch)
   elif not j['speed']:j['last']=now
 def release(self):
  for ch,j in self.jogs.items():
   if j['speed'] or j['delta']:self.stop_jog(ch)
  for key,ch in list(self.held):self.emit(key,2,ch,0,0.,0)
  self.held.clear()
def listen_reconnecting(b,lib,running,discover,sleep=time.sleep):
 """Release controller gestures on loss; rediscover ALSA numbering on return."""
 buf=ctypes.create_string_buffer(1024)
 waiting=False
 while running():
  handle=ctypes.c_void_p()
  try:
   devices=discover()
   if len(devices)!=1:raise OSError(errno.ENODEV,'Expected one FLX6 MIDI input')
   rc=lib.snd_rawmidi_open(ctypes.byref(handle),None,devices[0].encode(),2)
   if rc<0:raise OSError(-rc,'Cannot open FLX6 MIDI input')
  except (OSError,subprocess.SubprocessError) as e:
   if not waiting:print(f'Waiting for FLX6 MIDI: {e}',flush=True)
   waiting=True
   for _ in range(20):
    if not running():break
    sleep(.05)
   continue
  waiting=False
  print(f'Listening to {devices[0]} (input only)',flush=True)
  try:
   while running():
    n=lib.snd_rawmidi_read(handle,buf,len(buf))
    if n>0:b.feed(buf.raw[:n])
    elif n in (0,-errno.EAGAIN):sleep(.005)
    elif n!=-errno.EINTR:
     print(f'FLX6 MIDI read failed ({n}); reconnecting',flush=True)
     break
    b.tick()
  finally:
   try:b.release()
   finally:
    lib.snd_rawmidi_close(handle)
    # Never carry a partial message or old 14-bit MSB into a new connection.
    b.status=None;b.data=[];b.msb.clear()
  # Avoid a busy reconnect loop if ALSA still lists a failed device.
  for _ in range(20):
   if not running():break
   sleep(.05)
def main():
 p=argparse.ArgumentParser();p.add_argument('--mapping',default='/home/pompu_5/.mixxx/controllers/Pioneer-DDJ-FLX6.midi.xml');p.add_argument('--fifo',default='/home/pompu_5/rx3-rootfs/dev/rx3-control');p.add_argument('--replay');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 fd=None if a.dry_run else os.open(a.fifo,os.O_WRONLY|os.O_NONBLOCK)
 def emit(*cmd):
  if fd is not None:os.write(fd,struct.pack('<iiiifi',*cmd))
  if a.replay or a.dry_run:print(cmd,flush=True)
 b=Bridge(a.mapping,emit);print(f'Loaded {len(b.mapping)} MIDI bindings from {a.mapping}',flush=True)
 if a.replay:
  b.feed(open(a.replay,'rb').read());b.release();return
 # Preserve absolute jog counters across MIDI-reader restarts in this player session.
 player=subprocess.check_output(['pgrep','-x','rbp-pi'],text=True).strip()
 statefile='/home/pompu_5/rx3-midi-jog-state.json'
 try:
  previous=json.load(open(statefile))
  if previous.get('player')==player:
   for ch in (1,2):b.jogs[ch]['total']=int(previous['totals'][str(ch)])
 except (OSError,ValueError,KeyError,TypeError):pass
 lib=ctypes.CDLL('libasound.so.2');handle=ctypes.c_void_p()
 lib.snd_rawmidi_open.argtypes=[ctypes.POINTER(ctypes.c_void_p),ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int]
 lib.snd_rawmidi_read.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t];lib.snd_rawmidi_read.restype=ctypes.c_ssize_t
 lib.snd_rawmidi_close.argtypes=[ctypes.c_void_p]
 def discover():
  listing=subprocess.check_output(['amidi','-l'],text=True)
  return re.findall(r'^I[O ]\s+(hw:\S+)\s+.*DDJ-FLX6',listing,re.M)
 running=True
 def stop(*_):
  nonlocal running
  running=False
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 try:
  listen_reconnecting(b,lib,lambda:running,discover)
 finally:
  b.release()
  with open(statefile+'.tmp','w') as f:json.dump({'player':player,'totals':{ch:j['total'] for ch,j in b.jogs.items()}},f)
  os.replace(statefile+'.tmp',statefile)
  if fd is not None:os.close(fd)
if __name__=='__main__':main()
