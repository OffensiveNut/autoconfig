#!/usr/bin/env dash
export TMPFILE="$(mktemp)"
sudo true
rate-mirrors --save=$TMPFILE arch --max-delay=43200 &&
  grep -A 15 "# FINISHED AT:" "$TMPFILE" | head -n 16 >/tmp/top15 &&
  sudo mv /etc/pacman.d/mirrorlist /etc/pacman.d/mirrorlist-backup &&
  sudo mv /tmp/top15 /etc/pacman.d/mirrorlist
rm -f "$TMPFILE"
