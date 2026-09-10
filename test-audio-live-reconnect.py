"""One bounded FLX6 audio-driver detach/rebind; run as root on the Pi."""
from pathlib import Path
import subprocess,time,json
card=Path('/sys/class/sound/card2')
interface=(card/'device').resolve()
driver=(interface/'driver').resolve()
assert driver==Path('/sys/bus/usb/drivers/snd-usb-audio'),driver
assert (interface.parent/'product').read_text().strip()=='DDJ-FLX6'
name=interface.name
bound=sorted(p.name for p in driver.glob(interface.parent.name+":*") if p.is_symlink())
assert name in bound
pid=subprocess.check_output(['pgrep','-x','rbp-pi'],text=True).strip()
def state(label):
 out=subprocess.check_output(['python3',str(Path(__file__).resolve().with_name('test-audio-live-state.py'))],text=True)
 print(label,out.strip(),flush=True)
 return json.loads(out)
state('before')
try:
 for item in bound:
  if (driver/item).is_symlink():(driver/'unbind').write_text(item)
 time.sleep(2)
 offline=state('detached')
finally:
 for item in bound:
  if not (driver/item).is_symlink():(driver/'bind').write_text(item)
for _ in range(100):
 time.sleep(.2)
 recovered=json.loads(subprocess.check_output(['python3',str(Path(__file__).resolve().with_name('test-audio-live-state.py'))],text=True))
 if recovered['pair_state']==1:break
print('rebound',json.dumps(recovered),flush=True)
assert recovered['pid']==int(pid),'player restarted unexpectedly'
assert offline['pair_state']==2 and offline['real_handles']==[0,0],offline
assert recovered['pair_state']==1 and recovered['last_error']==0,recovered
assert (interface/'driver').resolve()==driver
print('PASS same player survived actual audio-driver loss and recovered both handles',flush=True)
