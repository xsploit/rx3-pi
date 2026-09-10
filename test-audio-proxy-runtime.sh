#!/bin/sh
# Isolated integration test; null PCMs by default.
# Optional second argument --flx6 uses real outputs: stop RX3/BiteDJ first.
# Never preload either test DSO into rbp-pi.
set -eu
cd "$(dirname "$0")"
rootfs=${1:-/home/pompu_5/rx3-rootfs}
compiler=${CC_ARM:-arm-linux-gnueabi-gcc}
mode=${2:-null}
case "$mode" in null|--flx6) ;; *) echo "Unknown mode: $mode" >&2; exit 2;; esac
test_dir=$(mktemp -d "$rootfs/tmp/rx3-proxy-test.XXXXXX")
trap 'rm -rf "$test_dir"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
"$compiler" -march=armv7-a -std=gnu11 -O2 -Wall -Wextra -Werror \
 -shared -fPIC -nostdlib -idirafter /usr/include -U_TIME_BITS -D_TIME_BITS=32 -U_FILE_OFFSET_BITS -D_FILE_OFFSET_BITS=32 -DRX3_AUDIO_PROXY_TEST \
 -Wl,--version-script=audio-proxy.map -o "$test_dir/proxy.so" \
 audio-proxy.c audio-alsa.c audio-recovery.c audio-handles.c audio-write.c audio-pacer.c \
 -L"$rootfs/usr/lib" -Wl,-rpath-link,"$rootfs/lib" -l:libasound.so.2 \
 -L"$rootfs/lib" -l:libdl.so.2 -l:libpthread.so.0 -l:librt.so.1 -l:libc.so.6 -lgcc
"$compiler" -march=armv7-a -std=gnu11 -O2 -Wall -Wextra -Werror \
 -shared -fPIC -nostdlib -idirafter /usr/include -U_TIME_BITS -D_TIME_BITS=32 -U_FILE_OFFSET_BITS -D_FILE_OFFSET_BITS=32 -DRX3_TEST_PRELOAD \
 -o "$test_dir/test.so" test-audio-proxy.c \
 -L"$rootfs/usr/lib" -Wl,-rpath-link,"$rootfs/lib" -l:libasound.so.2 \
 -L"$rootfs/lib" -l:libdl.so.2 -l:librt.so.1 -l:libc.so.6 -lgcc
cat > "$test_dir/alsa.conf" <<'CONFIG'
pcm.rx3out { type null }
pcm.rx3cue { type null }
pcm.null { type null }
CONFIG
inside=/tmp/$(basename "$test_dir")
if [ "$mode" = --flx6 ]; then
 sudo -n chroot --userspec="$(id -u):$(id -g)" "$rootfs" /bin/busybox env \
  "LD_PRELOAD=$inside/proxy.so:$inside/test.so" /bin/busybox true
else
 sudo -n chroot --userspec="$(id -u):$(id -g)" "$rootfs" /bin/busybox env \
  "LD_PRELOAD=$inside/proxy.so:$inside/test.so" "ALSA_CONFIG_PATH=$inside/alsa.conf" /bin/busybox true
fi
