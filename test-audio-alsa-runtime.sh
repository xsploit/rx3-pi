#!/bin/sh
# On the Pi: test only ALSA null PCMs inside the existing ARM32 runtime.
# Does not preload the player shim, open the FLX6, or restart any process.
set -eu
cd "$(dirname "$0")"
rootfs=${1:-/home/pompu_5/rx3-rootfs}
compiler=${CC_ARM:-arm-linux-gnueabi-gcc}
test -f "$rootfs/usr/lib/libasound.so.2"
test -f "$rootfs/lib/libdl.so.2"
test -f "$rootfs/lib/libc.so.6"
test_dso=$(mktemp "$rootfs/tmp/rx3-audio-test.XXXXXX.so")
trap 'rm -f "$test_dso"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
# Link against the actual runtime to record ALSA symbol versions. Unversioned
# references can bind its legacy ALSA_0.9 getter ABI instead of the rc4 ABI.
"$compiler" -march=armv7-a -std=gnu11 -O2 -Wall -Wextra -Werror \
 -shared -fPIC -nostdlib -idirafter /usr/include -DRX3_TEST_PRELOAD \
 -o "$test_dso" audio-recovery.c audio-alsa.c test-audio-alsa.c \
 -L"$rootfs/usr/lib" -Wl,-rpath-link,"$rootfs/lib" -l:libasound.so.2 \
 -L"$rootfs/lib" -l:libdl.so.2 -l:libc.so.6
sudo -n chroot --userspec="$(id -u):$(id -g)" "$rootfs" /bin/busybox env \
 "LD_PRELOAD=/tmp/$(basename "$test_dso")" /bin/busybox true
