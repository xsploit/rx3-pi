#!/bin/sh
# Host null-PCM integration test; no hardware access.
set -eu
cd "$(dirname "$0")"
test_dir=$(mktemp -d)
trap 'rm -rf "$test_dir"' EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
"${CC:-cc}" -std=gnu11 -O2 -Wall -Wextra -Werror -shared -fPIC \
 -DRX3_AUDIO_PROXY_TEST -Wl,--version-script=audio-proxy.map \
 -o "$test_dir/proxy.so" audio-proxy.c audio-alsa.c audio-recovery.c \
 audio-handles.c audio-write.c audio-pacer.c -lasound -ldl -pthread
"${CC:-cc}" -std=gnu11 -O2 -Wall -Wextra -Werror \
 -o "$test_dir/test" test-audio-proxy.c -lasound -ldl
cat > "$test_dir/alsa.conf" <<'CONFIG'
pcm.rx3out { type null }
pcm.rx3cue { type null }
pcm.null { type null }
CONFIG
ALSA_CONFIG_PATH="$test_dir/alsa.conf" LD_PRELOAD="$test_dir/proxy.so" "$test_dir/test"
