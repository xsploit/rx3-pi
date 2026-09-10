#!/usr/bin/env python3
"""Run the actual C bridge against evdev replay, testing native release output."""
import os,struct,subprocess,tempfile,time
from pathlib import Path
source=Path(__file__).resolve().parent
EV=struct.Struct('@llHHi');REPORT=struct.Struct('<BBHH')
def event(t,c,v):return EV.pack(0,0,t,c,v)
def contact():
 return b''.join(event(*x) for x in [(3,0x2f,0),(3,0x39,42),(3,0x35,1179),(3,0x36,360),(0,0,0)])
def wait_for(predicate):
 end=time.monotonic()+2
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.01)
 raise AssertionError('Timed out waiting for bridge output')
with tempfile.TemporaryDirectory() as tmp:
 d=Path(tmp);binary=d/'bridge';state=d/'state';control=d/'control';control.touch()
 subprocess.run(['gcc','-O2',f'-DUI_STATE="{state}"',f'-DUI_CONTROL="{control}"','-o',str(binary),str(source/'touch-bridge.c')],check=True)
 def run(mode):
  out=d/mode;out.touch()
  p=subprocess.Popen([str(binary),'--replay',str(out),'--fullscreen'],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
  def reports():
   raw=out.read_bytes();return [REPORT.unpack_from(raw,i) for i in range(0,len(raw)-5,6)]
  try:
   p.stdin.write(contact());p.stdin.flush();wait_for(lambda:any(x[0] for x in reports()))
   if mode=='eof':p.stdin.close()
   elif mode=='term':p.terminate()
   else:
    p.stdin.write(event(0,3,0)+event(3,0x35,20)+event(0,0,0));p.stdin.flush()
    wait_for(lambda:len(reports())>=10 and all(x[0]==0 for x in reports()[-10:]))
    # Remaining motion without a fresh tracking ID must not recreate the held press.
    mark=len(reports());p.stdin.write(event(3,0x36,900)+event(0,0,0));p.stdin.flush();time.sleep(.08)
    assert all(x[0]==0 for x in reports()[mark:])
    p.stdin.write(contact());p.stdin.flush();wait_for(lambda:any(x[0] for x in reports()[mark:]))
    p.terminate()
   assert p.wait(timeout=2)==0,p.stderr.read()
   packets=reports();assert len(packets)>=11
   assert all(x[0]==0 for x in packets[-10:]),packets[-10:]
   assert any(x[0]==1 for x in packets)
   print('PASS',mode,'releases active native touch')
  finally:
   if p.poll() is None:p.kill();p.wait()
 for mode in ('eof','term','dropped'):run(mode)
 out=d/'absent-out';out.touch()
 p=subprocess.Popen([str(binary),str(d/'missing-device'),str(out),'--fullscreen'],stderr=subprocess.PIPE)
 try:
  time.sleep(.15);assert p.poll() is None
  p.terminate();assert p.wait(timeout=2)==0
  print('PASS absent device waits and stops cleanly')
 finally:
  if p.poll() is None:p.kill();p.wait()
