#!/bin/sh
# Build the compatibility helpers. Nothing is installed or started.
#
#   sh build.sh native            Pi-side helpers and host tests (no firmware needed)
#   sh build.sh shim RUNTIME      ARM32 player shim + clock stub, linked against RUNTIME
#   sh build.sh all RUNTIME       both (sh build.sh RUNTIME also works)
#
# ./rx3 build runs this with the paths from rx3.conf. Environment overrides:
# RX3_BUILD (output directory, default ./build), CC, CC_ARM, AS_ARM,
# OBJCOPY_ARM and RX3_ALSA_CARD (ALSA card ID for the shim, default DDJFLX6).
set -eu
cd "$(dirname "$0")"
usage() {
 sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//' >&2
 exit 2
}
mode=${1:-}
case "$mode" in
 native) runtime= ;;
 shim|all) runtime=${2:-${RX3_RUNTIME:-}} ;;
 '') usage ;;
 -h|--help) usage ;;
 *) runtime=$mode; mode=all ;;
esac
out=${RX3_BUILD:-build}
cc=${CC:-gcc}
missing() {
 echo "Missing build tool: $1. Install it with: sudo apt install $2" >&2
 echo "Run ./rx3 doctor for a full list of what is missing." >&2
 exit 1
}
mkdir -p "$out"
if [ "$mode" = native ] || [ "$mode" = all ]; then
 command -v "$cc" >/dev/null 2>&1 || missing "$cc" build-essential
 command -v pkg-config >/dev/null 2>&1 || missing pkg-config pkg-config
 pkg-config --exists libdrm || missing 'libdrm development files (xf86drm.h)' libdrm-dev
 pkg-config --exists freetype2 || missing 'FreeType development files' libfreetype-dev
 flags=$(pkg-config --cflags --libs freetype2 libdrm)
 # shellcheck disable=SC2086
 "$cc" -O3 -o "$out/rx3-fb-present" fb-present.c $flags
 "$cc" -O2 -o "$out/rx3-touch-bridge" touch-bridge.c
 # shellcheck disable=SC2086
 "$cc" -O2 -o "$out/test-frame-exchange" test-frame-exchange.c $flags
 "$cc" -O2 -o "$out/test-frame-scale" test-frame-scale.c
 "$cc" -I . -o "$out/test-mixer-layout" test-mixer-layout.c
 "$cc" -O2 -o "$out/test-mixer-state" test-mixer-state.c mixer-state.c
 for test in test-tempo-step test-tempo-input test-pad-bank test-pad-intent; do
  "$cc" -O2 -o "$out/$test" "$test.c"
 done
 "$cc" -std=c11 -O2 -o "$out/test-audio-recovery" audio-recovery.c test-audio-recovery.c
 echo "Built Pi-side helpers in $out: rx3-fb-present rx3-touch-bridge (and host tests)"
fi
if [ "$mode" = shim ] || [ "$mode" = all ]; then
 if [ -z "$runtime" ]; then
  echo "Give the assembled runtime directory: sh build.sh $mode /path/to/runtime" >&2
  echo "(./rx3 assemble creates it; ./rx3 build passes it automatically.)" >&2
  exit 2
 fi
 as_arm=${AS_ARM:-arm-linux-gnueabi-as}
 objcopy_arm=${OBJCOPY_ARM:-arm-linux-gnueabi-objcopy}
 command -v "$as_arm" >/dev/null 2>&1 || missing "$as_arm" binutils-arm-linux-gnueabi
 command -v "$objcopy_arm" >/dev/null 2>&1 || missing "$objcopy_arm" binutils-arm-linux-gnueabi
 # A failed build must never leave an older shim behind for ./rx3 install.
 rm -f "$out/fbshim-audio.so" "$out/fbshim.so" "$out/pi-clock.o" "$out/pi-clock.bin"
 RX3_BUILD=$out sh build-audio-candidate.sh "$runtime"
 cp "$out/fbshim-audio.so" "$out/fbshim.so"
 "$as_arm" -o "$out/pi-clock.o" pi-clock.S
 "$objcopy_arm" -O binary -j .text "$out/pi-clock.o" "$out/pi-clock.bin"
 echo "Built ARM32 shim and clock stub in $out: fbshim.so pi-clock.bin"
fi
