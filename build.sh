#!/bin/sh
set -eu
cd "$(dirname "$0")"
mkdir -p build
arm-linux-gnueabi-gcc -march=armv7-a -shared -fPIC -O2 -fomit-frame-pointer -fno-builtin -nostdlib -o build/fbshim.so fbshim.c control-shim.c native-touch.c native-ui.c frame-publish.c mixer-state.c native-mixer.c
gcc -O2 -o build/rx3-fb-present fb-present.c $(pkg-config --cflags --libs freetype2 libdrm)
gcc -O2 -o build/rx3-touch-bridge touch-bridge.c
arm-linux-gnueabi-as -o build/pi-clock.o pi-clock.S
arm-linux-gnueabi-objcopy -O binary -j .text build/pi-clock.o build/pi-clock.bin
