#!/bin/sh
set -eu
cd "$(dirname "$0")"
for tool in gcc pkg-config arm-linux-gnueabi-as arm-linux-gnueabi-objcopy; do
 command -v "$tool" >/dev/null 2>&1 || {
  echo "Missing build tool: $tool. See README.md Build for Debian packages." >&2
  exit 1
 }
done
pkg-config --exists freetype2 libdrm || {
 echo "Missing FreeType/libdrm development files. On Debian: sudo apt install pkg-config libfreetype-dev libdrm-dev" >&2
 exit 1
}
mkdir -p build
sh build-audio-candidate.sh "${1:-/home/pompu_5/rx3-rootfs}"
cp build/fbshim-audio.so build/fbshim.so
gcc -O3 -o build/rx3-fb-present fb-present.c $(pkg-config --cflags --libs freetype2 libdrm)
gcc -O2 -o build/rx3-touch-bridge touch-bridge.c
arm-linux-gnueabi-as -o build/pi-clock.o pi-clock.S
arm-linux-gnueabi-objcopy -O binary -j .text build/pi-clock.o build/pi-clock.bin
