#!/usr/bin/env python3
"""Root-only Linux uinput reconnect test. Uses isolated files and EVIOCGRAB."""
import fcntl,os,struct,subprocess,tempfile,time
from pathlib import Path
source=Path(__file__).resolve().parent
EV=struct.Struct('@llHHi');REPORT=struct.Struct('<BBHH')
def wait_for(predicate):
 end=time.monotonic()+5
 while time.monotonic()<end:
  if predicate():return
  time.sleep(.02)
 raise AssertionError('Timed out waiting for evdev reconnect')
class Device:
 def __init__(self,serial,xmax,ymax):
  self.fd=os.open('/dev/uinput',os.O_WRONLY|os.O_NONBLOCK)
  try:
   fcntl.ioctl(self.fd,0x40045564,3) # UI_SET_EVBIT(EV_ABS)
   limits={47:9,53:xmax,54:ymax,57:65535}
   for code in limits:fcntl.ioctl(self.fd,0x40045567,code) # UI_SET_ABSBIT
   self.name=f'rx3-isolated-touch-test-{os.getpid()}-{serial}'
   header=struct.pack('<80sHHHHI',self.name.encode(),6,1,1,1,0)
   maxima=[limits.get(i,0) for i in range(64)]
   os.write(self.fd,header+struct.pack('<256i',*(maxima+[0]*192)))
   fcntl.ioctl(self.fd,0x5501) # UI_DEV_CREATE
   self.path=None
   def locate():
    for p in Path('/sys/class/input').glob('event*/device/name'):
     if p.read_text().strip()==self.name:
      self.path=Path('/dev/input')/p.parent.parent.name;return self.path.exists()
   wait_for(locate)
  except BaseException:
   os.close(self.fd);self.fd=None;raise
 def contact(self,x,y):
  for t,c,v in [(3,47,0),(3,57,1),(3,53,x),(3,54,y),(0,0,0)]:os.write(self.fd,EV.pack(0,0,t,c,v))
 def close(self):
  if self.fd is not None:
   try:fcntl.ioctl(self.fd,0x5502)
   finally:os.close(self.fd);self.fd=None
if os.geteuid()!=0:raise SystemExit('Run as root on Linux with /dev/uinput available')
with tempfile.TemporaryDirectory(prefix='rx3-touch-test-') as tmp:
 d=Path(tmp);binary=d/'bridge';out=d/'reports';control=d/'control';link=d/'panel';log=d/'log'
 out.touch();control.touch()
 subprocess.run(['gcc','-O2',f'-DUI_STATE="{d / "state"}"',f'-DUI_CONTROL="{control}"','-o',str(binary),str(source/'touch-bridge.c')],check=True)
 def reports():
  raw=out.read_bytes();return [REPORT.unpack_from(raw,i) for i in range(0,len(raw)-5,6)]
 devices=[];p=None
 with log.open('wb') as errors:
  try:
   p=subprocess.Popen([str(binary),str(link),str(out),'--fullscreen','--exclusive'],stderr=errors)
   wait_for(lambda:'waiting for touch device' in log.read_text())
   first=Device(1,1199,1919);devices.append(first);link.symlink_to(first.path)
   wait_for(lambda:log.read_text().count('touch input connected:')==1)
   # EVIOCGRAB is held before this report: no other input consumer receives it.
   first.contact(600,960);wait_for(lambda:any(r[0] for r in reports()))
   first_xy=next(r[2:] for r in reports() if r[0])
   link.unlink();first.close()
   wait_for(lambda:len(reports())>=11 and all(r[0]==0 for r in reports()[-10:]))
   assert p.poll() is None
   second=Device(2,599,959);devices.append(second);link.symlink_to(second.path)
   wait_for(lambda:log.read_text().count('touch input connected:')==2)
   mark=len(reports());second.contact(300,480)
   wait_for(lambda:any(r[0] for r in reports()[mark:]))
   second_xy=next(r[2:] for r in reports()[mark:] if r[0])
   assert first_xy==second_xy,(first_xy,second_xy)
   p.terminate();assert p.wait(timeout=3)==0
   assert all(r[0]==0 for r in reports()[-10:])
   print('PASS real evdev loss/reopen, release, refreshed axis ranges, continued touch, SIGTERM')
   print('Native coordinates preserved:',first_xy)
  finally:
   if p is not None and p.poll() is None:p.kill();p.wait()
   for device in devices:device.close()
