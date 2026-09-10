import importlib.util, pathlib, tempfile, unittest
spec=importlib.util.spec_from_file_location('bridge',pathlib.Path(__file__).with_name('flx6-rx3.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Navigation(unittest.TestCase):
 def test_bitedj_navigation_bytes(self):
  controls=[('[Tab]','library',0x96,0x7a),('[Tab]','PioneerDDJFLX6.backPressed',0x96,0x65),('[Library]','PioneerDDJFLX6.browseRotate',0xb6,0x40),('[Library]','MoveFocusForward',0x96,0x41)]
  xml='<root><controls>'+''.join(f'<control><group>{g}</group><key>{k}</key><status>{s}</status><midino>{n}</midino></control>' for g,k,s,n in controls)+'</controls></root>'
  with tempfile.NamedTemporaryFile(mode='w',suffix='.xml') as f:
   f.write(xml);f.flush();events=[];b=m.Bridge(f.name,lambda *a:events.append(a))
   for packet in ([0x96,0x7a],[127,0xf8,0x7a,0],[0x96,0x65,127,0x86,0x65,64],[0xb6,0x40,1,0x40,127],[0x96,0x41,127,0x41,0]):b.feed(packet)
  self.assertEqual(events,[(0x202,0,0,0,0.,0x4256),(0x420d,0,0,0,0.,0x424b),(0x420c,4,0,1,0.,0x4252),(0x420c,4,0,-1,0.,0x4252),(0x420c,0,0,0,0.,0x4250)])
if __name__=='__main__':unittest.main()
