#!/bin/sh
# Stop only RX3 processes; release MIDI/audio/display for the preserved BiteDJ.
set -eu
exec 9>/home/pompu_5/.rx3-runtime.lock
flock -x 9
python3 - <<'PY'
import os,signal,time
from pathlib import Path
home='/home/pompu_5/'
def targets():
 result={'midi':[],'touch':[],'player':[],'display':[]}
 for d in Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   if d.stat().st_uid!=os.getuid():continue
   args=(d/'cmdline').read_bytes().split(b'\0');args=[os.fsdecode(a) for a in args if a]
   if not args:continue
   exe=os.path.basename(args[0])
   if exe=='rbp-pi' and args[0]=='/root/pdj/rbp-pi':kind='player'
   elif exe=='rx3-fb-present' and args[1:]==[home+'rx3-rootfs/dev/fb0']:kind='display'
   elif exe=='rx3-touch-bridge' and len(args)==3 and args[2]==home+'rx3-rootfs/dev/tsc2007_2-0048':kind='touch'
   elif exe=='python3' and len(args)==2 and args[1] in ('flx6-rx3.py',home+'flx6-rx3.py'):kind='midi'
   else:continue
   result[kind].append(int(d.name))
  except (OSError,ValueError):continue
 return result
for kind in ('midi','touch','player','display'):
 for pid in targets()[kind]:
  try:os.kill(pid,signal.SIGTERM)
  except ProcessLookupError:pass
 deadline=time.monotonic()+5
 while targets()[kind] and time.monotonic()<deadline:time.sleep(.05)
 if targets()[kind]:raise SystemExit(f'{kind} did not stop cleanly; left it for inspection.')
print('RX3 stopped; MIDI, audio and display released. BiteDJ files unchanged.')
PY
