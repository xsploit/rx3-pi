#!/usr/bin/env python3
"""Send one native RX3 key (or the USB1 mount event) to a running player.
Usage: pi-control.py mount | NAME_OR_KEY [CHANNEL [ANALOG]]; needs RX3_RUNTIME."""
import os,struct,time,sys
root=os.environ.get('RX3_RUNTIME')
if not root or len(sys.argv)<2:sys.exit(__doc__)
keys={'usb1':0x209,'usb2':0x20a,'browse':0x202,'source':0x201,'play':0x4101,'cue':0x4102,'load':0x4311,'enter':0x420c,'back':0x420d,'headphones':0x4406,'hpmix':0x4405,'hpcue':0x5020}
if sys.argv[1]=='mount':
 f=os.open(root+'/proc/udev_usb1',os.O_RDWR|os.O_NONBLOCK);os.write(f,b'mount /media/usb1/sda1');os.close(f)
else:
 name=sys.argv[1]; key=keys.get(name)
 if key is None:key=int(name,0)
 ch=int(sys.argv[2]) if len(sys.argv)>2 else 0
 f=os.open(root+'/dev/rx3-control',os.O_RDWR|os.O_NONBLOCK)
 analog=float(sys.argv[3]) if len(sys.argv)>3 else None
 for op in ((4,) if analog is not None else (0,2)):
  os.write(f,struct.pack('<iiiifi',key,op,ch,0,analog or 0.,0));time.sleep(.1)
 os.close(f)
