#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p build
sh build-audio-candidate.sh "${1:-/home/pompu_5/rx3-rootfs}"
cp build/fbshim-audio.so build/fbshim.so
gcc -O2 -o build/rx3-fb-present fb-present.c $(pkg-config --cflags --libs freetype2 libdrm)
gcc -O2 -o build/rx3-touch-bridge touch-bridge.c
arm-linux-gnueabi-as -o build/pi-clock.o pi-clock.S
arm-linux-gnueabi-objcopy -O binary -j .text build/pi-clock.o build/pi-clock.bin
