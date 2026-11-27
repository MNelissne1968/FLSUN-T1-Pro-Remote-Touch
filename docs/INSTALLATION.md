# Installation guide — v0.2.1

The Python application was tested on one FLSUN T1 Pro. The packaged installer and /opt installation layout are new and have not been hardware-tested. Do not install over an existing Remote Touch setup. Read the README safety notes first.

## 1. Connect

The printer must already have working Wi-Fi/network access, SSH credentials and sudo rights. Find its IP in your router's connected-device list. Replace PRINTER_IP below with that address. On Windows PowerShell:

```powershell
ssh pi@PRINTER_IP
```

Use your own SSH account if different. Check the original TUI is running and the devices match:

```sh
ps -p 1 -o comm=
ps -ef | grep '[T]UI'
python3 --version
cat /sys/class/graphics/fb0/virtual_size
cat /sys/class/graphics/fb0/bits_per_pixel
cat /sys/class/graphics/fb0/stride
cat /sys/class/input/event1/device/name
cat /etc/pointercal
```

Expected: systemd, Python 3.7 or compatible, 480,272, 32, 1920, tlsc6x_touch. The tested calibration was:

```text
-719 62098 1205500 -65727 81 17556672 65536 480 272 0
```

If anything differs, stop and report the configuration rather than guessing coordinates or device numbers. Do not overwrite pointercal.

## 2. Transfer files

Download the repository ZIP from GitHub, extract it on your PC, and open PowerShell in the extracted directory. In the SSH session create a staging directory:

```sh
mkdir -p ~/flsun-remote-touch-staging
```

In local PowerShell:

```powershell
scp -O remote_touch_v021.py flsun-remote-touch.service install.sh uninstall.sh pi@PRINTER_IP:flsun-remote-touch-staging/
```

The -O option uses legacy SCP, which worked on the tested printer when modern SFTP failed.

## 3. Install

With the printer idle and cold, in the SSH session:

```sh
cd ~/flsun-remote-touch-staging
sudo sh install.sh
sudo systemd-analyze verify /etc/systemd/system/flsun-remote-touch.service
```

Alternatively, on a fresh installation only, manually install the files:

```sh
sudo install -d -o root -g root -m 0755 /opt/flsun-remote-touch
sudo install -o root -g root -m 0644 remote_touch_v021.py /opt/flsun-remote-touch/
sudo install -o root -g root -m 0644 flsun-remote-touch.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Do not overwrite an existing service. Review verification warnings before continuing. Stop any manually running Remote Touch instance before starting the service.

```sh
sudo systemctl start flsun-remote-touch.service
sudo systemctl status flsun-remote-touch.service --no-pager -l
```

## 4. Open the browser

In a separate local PowerShell window:

```powershell
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8765:127.0.0.1:8765 pi@PRINTER_IP
```

Keep that window open. Visit http://localhost:8765 in your browser. Confirm the live image is correct before enabling touch. Only test known, harmless navigation buttons with the printer idle and cold. Disable touch when monitoring a print. Keep physical access to the power switch.

## 5. Automatic startup

Once verified:

```sh
sudo systemctl enable flsun-remote-touch.service
sudo systemctl is-enabled flsun-remote-touch.service
```

When safe, power-cycle the printer, reconnect the SSH tunnel and verify the page. The service starts on the printer; the PC tunnel must still be opened.

## Troubleshooting

- HTTP 403: reload the page or open a fresh private window; the token changes on restart. Use localhost or 127.0.0.1, not the printer IP.
- No image: check SSH tunnel, TUI and framebuffer; inspect service logs.
- Incorrect touch: disable touch immediately; verify device and calibration. Do not experiment with unknown buttons.
- Hostname resolution warning from sudo: observed on the tested printer; check the actual command result.
- Service logs: `sudo journalctl -u flsun-remote-touch.service -n 50 --no-pager`.

## Removal

From the staging directory, with the printer idle:

```sh
sudo sh uninstall.sh
```

This removes only the packaged /opt installation and its service. It intentionally refuses to remove the original development installation under /home/pi.
