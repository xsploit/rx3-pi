#!/bin/sh
set -eu
cd /home/pompu_5
exec 9>/home/pompu_5/.rx3-runtime.lock
flock -x 9
new_player=0
if ! pgrep -x rbp-pi >/dev/null; then
new_player=1
# Reset the touchscreen's displayed controls to match firmware startup defaults.
python3 - <<'PY_STATE'
import os,struct
with os.fdopen(os.open('/home/pompu_5/rx3-rootfs/dev/rx3-ui-state',os.O_RDWR|os.O_CREAT,0o600),'r+b') as f:
    f.write(struct.pack('<I6fII',0x52583332,1,.6,0,1,.5,.5,0,1))
PY_STATE
nohup sudo -n chroot --userspec=1000:44 --groups=29,44,995,991 /home/pompu_5/rx3-rootfs /bin/busybox env LD_PRELOAD=/lib/fbshim.so /root/pdj/rbp-pi -a > /home/pompu_5/rx3-player.log 2>&1 < /dev/null 9>&- &
fi
if ! pgrep -x rx3-fb-present >/dev/null; then
 nohup /home/pompu_5/rx3-fb-present /home/pompu_5/rx3-rootfs/dev/fb0 --fullscreen > /home/pompu_5/rx3-present.log 2>&1 < /dev/null 9>&- &
fi
if ! pgrep -f '^(/home/pompu_5/|./)rx3-touch-bridge /dev/input/' >/dev/null; then
 nohup /home/pompu_5/rx3-touch-bridge /dev/input/by-path/platform-1f00080000.i2c-event /home/pompu_5/rx3-rootfs/dev/tsc2007_2-0048 --fullscreen > /home/pompu_5/rx3-touch.log 2>&1 < /dev/null 9>&- &
fi
# A repeated start also restores missing helper processes.
if ! pgrep -f '^python3 (/home/pompu_5/)?flx6-rx3.py$' >/dev/null; then
 nohup python3 /home/pompu_5/flx6-rx3.py > /home/pompu_5/rx3-midi.log 2>&1 < /dev/null 9>&- &
fi
if [ "$new_player" = 0 ]; then
 echo 'RX3 already running; checked display, touch, and MIDI helpers.'
 exit 0
fi
# Storage workers initialize after the display; report the existing read-only USB.
sleep 10
if pgrep -x rbp-pi >/dev/null && mountpoint -q /home/pompu_5/rx3-rootfs/media/usb1/sda1; then
 python3 /home/pompu_5/pi-control.py mount
fi
if pgrep -x rbp-pi >/dev/null && mountpoint -q /home/pompu_5/rx3-rootfs/media/usb2/sdb1/Contents; then
 python3 - <<'PY_USB2'
import os
f=os.open('/home/pompu_5/rx3-rootfs/proc/udev_usb2',os.O_RDWR|os.O_NONBLOCK)
os.write(f,b'mount /media/usb2/sdb1')
os.close(f)
PY_USB2
fi
