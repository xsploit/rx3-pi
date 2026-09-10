"""Overlapping MIDI pads must not release a newer action in the same slot."""
import importlib.util,pathlib,tempfile
s=importlib.util.spec_from_file_location('bridge',pathlib.Path(__file__).with_name('flx6-rx3.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
with tempfile.NamedTemporaryFile(mode='w') as f:
 f.write('<root/>');f.flush();events=[];b=m.Bridge(f.name,lambda *x:events.append(x))
 for d,status in [(1,0x97),(2,0x99)]:
  for i in range(2):
   for note,mode in [(i,'pad-hotcue'),(0x20+i,'pad-beatjump'),(0x60+i,'pad-beatloop')]:b.mapping[(status,note)]=(0x4117+i,d,mode)
 def msg(status,note,value):b.feed(bytes([status,note,value]))
 # Hold two cues on deck1 and one on deck2.
 msg(0x97,0,127);msg(0x97,1,127);msg(0x99,0,127);events.clear()
 msg(0x97,0x60,127)
 assert events==[(0x4117,2,1,0,0.,0x5040),(0x4118,2,1,0,0.,0x5040),(0x4117,0,1,0,0.,0x5041)],events
 events.clear()
 msg(0x87,0,64);msg(0x97,1,0) # late old-bank releases
 msg(0x97,0x60,127) # duplicate press cannot toggle the loop
 assert events==[]
 assert b.pad_held=={(0x4117,2):0,(0x4117,1):1}
 msg(0x97,0x60,0)
 assert events==[(0x4117,2,1,0,0.,0x5041)]
 # A disconnect releases the remaining deck2 press and clears ownership.
 events.clear();b.release()
 assert events==[(0x4117,2,2,0,0.,0)]
 assert not b.pad_held and not b.held
 events.clear();msg(0x99,0,0);assert not events
 msg(0x99,0,127);assert events==[(0x4117,0,2,0,0.,0x5040)]
print('PASS cross-bank release order, late NoteOff, deck isolation, duplicate press, disconnect reset')
