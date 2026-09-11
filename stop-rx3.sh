#!/bin/sh
# Compatibility name for ./rx3 stop: releases MIDI, audio, display and mounts.
here=$(dirname "$(readlink -f "$0")")
if [ ! -f "$here/rx3tool/launch.py" ]; then
 echo "stop-rx3.sh now needs the rest of the rx3-pi checkout. Run ./rx3 stop from the checkout." >&2
 exit 2
fi
exec python3 "$here/rx3" stop "$@"
