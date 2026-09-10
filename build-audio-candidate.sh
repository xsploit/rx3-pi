#!/bin/sh
# Builds the ARM32 player shim separately. build.sh copies it to build/fbshim.so.
# This script never deploys or overwrites the running runtime library.
set -eu
cd "$(dirname "$0")"
rootfs=${1:-/home/pompu_5/rx3-rootfs}
compiler=${CC_ARM:-arm-linux-gnueabi-gcc}
test -f "$rootfs/usr/lib/libasound.so.2"
mkdir -p build
"$compiler" -march=armv7-a -shared -fPIC -O2 -fomit-frame-pointer \
 -fno-builtin -nostdlib -idirafter /usr/include \
 -U_TIME_BITS -D_TIME_BITS=32 -U_FILE_OFFSET_BITS -D_FILE_OFFSET_BITS=32 \
 -DRX3_AUDIO_RECOVERY -Wl,--version-script=fbshim-audio.map \
 -o build/fbshim-audio.so fbshim.c control-shim.c native-touch.c native-ui.c \
 frame-publish.c mixer-state.c native-mixer.c native-pad-modes.c \
 audio-proxy.c audio-alsa.c audio-recovery.c audio-handles.c audio-write.c audio-pacer.c \
 -L"$rootfs/usr/lib" -Wl,-rpath-link,"$rootfs/lib" -l:libasound.so.2 \
 -L"$rootfs/lib" -l:libdl.so.2 -l:libpthread.so.0 -l:librt.so.1 -l:libc.so.6 -lgcc
