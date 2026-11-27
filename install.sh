#!/bin/sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Run with sudo sh install.sh"; exit 1; }
cd "$(dirname "$0")"
dest=/opt/flsun-remote-touch
unit=/etc/systemd/system/flsun-remote-touch.service
[ ! -e "$dest" ] && [ ! -e "$unit" ] || { echo "Existing installation detected; stop and review manually."; exit 1; }
[ "$(cat /proc/1/comm)" = systemd ]
[ "$(cat /sys/class/graphics/fb0/virtual_size)" = 480,272 ]
[ "$(cat /sys/class/graphics/fb0/bits_per_pixel)" = 32 ]
[ "$(cat /sys/class/graphics/fb0/stride)" = 1920 ]
[ "$(cat /sys/class/input/event1/device/name)" = tlsc6x_touch ]
[ -c /dev/fb0 ] && [ -c /dev/input/event1 ] && [ -r /etc/pointercal ]
/usr/bin/python3 -c 'import ast; ast.parse(open("remote_touch_v021.py").read())'
echo "Installing files only. Review calibration and safety instructions before starting."
install -d -o root -g root -m 0755 "$dest"
install -o root -g root -m 0644 remote_touch_v021.py "$dest/"
install -o root -g root -m 0644 flsun-remote-touch.service "$unit"
systemctl daemon-reload
echo "Installed. Follow docs/INSTALLATION.md to start and enable."
