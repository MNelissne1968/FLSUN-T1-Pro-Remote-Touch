#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Run with sudo sh uninstall.sh"; exit 1; }
unit=/etc/systemd/system/flsun-remote-touch.service
dest=/opt/flsun-remote-touch
[ -f "$unit" ] && grep -Fxq 'ExecStart=/usr/bin/python3 -u /opt/flsun-remote-touch/remote_touch_v021.py' "$unit" || { echo "Expected community service not found; refusing removal."; exit 1; }
systemctl stop flsun-remote-touch.service
systemctl disable flsun-remote-touch.service
rm -- "$unit" "$dest/remote_touch_v021.py"
rmdir "$dest" || echo "Additional files retained in $dest"
systemctl daemon-reload
echo "Remote Touch removed."
