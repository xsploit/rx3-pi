#!/bin/sh
# Run on the existing Pi setup. USB1 remains read-only; USB2 is a test library view.
set -eu
base=/home/pompu_5/rx3-rootfs
src=$base/media/usb1/sda1
dst=$base/media/usb2/sdb1
mountpoint -q "$src"
if mountpoint -q "$dst"; then
 echo 'USB2 root is mounted already; inspect before replacing it.' >&2
 exit 1
fi
mkdir -p "$dst/PIONEER/rekordbox"
# Never overwrite an existing local database (it may contain new cues/history).
for file in "$src/PIONEER/rekordbox/"*; do
 name=${file##*/}
 if [ -f "$file" ] && [ ! -e "$dst/PIONEER/rekordbox/$name" ]; then
  cp "$file" "$dst/PIONEER/rekordbox/$name"
  chmod u+rw "$dst/PIONEER/rekordbox/$name"
 fi
done
for file in "$src/PIONEER/"*; do
 if [ -f "$file" ] && [ ! -e "$dst/PIONEER/${file##*/}" ]; then cp "$file" "$dst/PIONEER/"; fi
done
for part in Contents Music PIONEER/Artwork; do
 if [ -d "$src/$part" ]; then
  mkdir -p "$dst/$part"
  if ! mountpoint -q "$dst/$part"; then
   sudo -n mount --bind "$src/$part" "$dst/$part"
   sudo -n mount -o remount,bind,ro "$dst/$part"
  fi
 fi
done
mkdir -p "$dst/PIONEER/USBANLZ"
# The firmware opens detailed waveforms O_RDWR, including during playback.
# Preserve any local cue edits when refreshing from the original export.
rsync -a --ignore-existing "$src/PIONEER/USBANLZ/" "$dst/PIONEER/USBANLZ/"
printf '%s\n' 'Local database and analysis ready; original music stays read-only.'
