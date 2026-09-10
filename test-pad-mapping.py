import importlib.util,tempfile,pathlib
s=importlib.util.spec_from_file_location('bridge',pathlib.Path(__file__).with_name('flx6-rx3.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
controls=[]
for deck,status in [(1,0x97),(2,0x99)]:
 for i in range(8):
  for key,note in [(f'hotcue_{i+1}_activate',i),('PioneerDDJFLX6.beatjumpPadPressed',0x20+i)]:
   controls.append(f'<control><group>[Channel{deck}]</group><key>{key}</key><status>{status}</status><midino>{note}</midino></control>')
with tempfile.NamedTemporaryFile(mode='w') as f:
 f.write('<root><controls>'+''.join(controls)+'</controls></root>');f.flush();events=[];b=m.Bridge(f.name,lambda *x:events.append(x))
 for deck,status in [(1,0x97),(2,0x99)]:
  for i in range(8):
   for note,mode in [(i,0x5040),(0x20+i,0x5043)]:
    events.clear();b.feed(bytes([status,note,127,status-16,note,64]))
    assert events==[(0x4117+i,0,deck,0,0.,mode),(0x4117+i,2,deck,0,0.,mode)],events
print('PASS both decks: eight hot cues and eight beat-jump press/release mappings')
