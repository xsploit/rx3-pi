#!/bin/sh
# Builds the ARM32 player shim separately. build.sh copies it to build/fbshim.so.
# This script never deploys or overwrites the running runtime library.
# Usage: sh build-audio-candidate.sh RUNTIME   (the assembled RX3 runtime)
set -eu
cd "$(dirname "$0")"
rootfs=${1:-${RX3_RUNTIME:-}}
out=${RX3_BUILD:-build}
compiler=${CC_ARM:-arm-linux-gnueabi-gcc}
card=${RX3_ALSA_CARD:-DDJFLX6}
if [ -z "$rootfs" ]; then
 echo "Usage: sh build-audio-candidate.sh /path/to/assembled/runtime" >&2
 exit 2
fi
case "$card" in
 *[!A-Za-z0-9_]*|'') echo "Invalid ALSA card ID: $card" >&2; exit 2 ;;
esac
command -v "$compiler" >/dev/null 2>&1 || {
 echo "Missing ARM32 compiler: $compiler. On Debian: sudo apt install gcc-arm-linux-gnueabi" >&2
 exit 1
}
test -f "$rootfs/usr/lib/libasound.so.2" || {
 echo "Missing assembled RX3 runtime: $rootfs/usr/lib/libasound.so.2" >&2
 echo "Create it with ./rx3 recover and ./rx3 assemble (see README.md)." >&2
 exit 1
}
mkdir -p "$out"
"$compiler" -march=armv7-a -shared -fPIC -O2 -fomit-frame-pointer \
 -fno-builtin -nostdlib -idirafter /usr/include \
 -U_TIME_BITS -D_TIME_BITS=32 -U_FILE_OFFSET_BITS -D_FILE_OFFSET_BITS=32 \
 -DRX3_AUDIO_RECOVERY "-DRX3_CTL_DEVICE=\"hw:CARD=$card\"" \
 -Wl,--version-script=fbshim-audio.map \
 -o "$out/fbshim-audio.so" fbshim.c control-shim.c native-touch.c native-ui.c \
 frame-publish.c native-grid.c native-tempo25.c mixer-state.c native-mixer.c native-pad-modes.c \
 audio-proxy.c audio-alsa.c audio-recovery.c audio-handles.c audio-write.c audio-pacer.c \
 -L"$rootfs/usr/lib" -Wl,-rpath-link,"$rootfs/lib" -l:libasound.so.2 \
 -L"$rootfs/lib" -l:libdl.so.2 -l:libpthread.so.0 -l:librt.so.1 -l:libc.so.6 -lgcc
