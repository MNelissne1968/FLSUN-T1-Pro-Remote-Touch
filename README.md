# FLSUN T1 Pro Remote Touch

**Restore your touchscreen. Without replacing it.**

An independent, community-driven project that displays the original FLSUN T1 Pro touchscreen in a web browser and allows interactive control, even when the physical display is disconnected.

## Status

**v0.2.1 — first hardware-tested milestone. Active development.**

Tested on one FLSUN T1 Pro with a disconnected touchscreen: live display, menu navigation, firmware version check and automatic startup after a power cycle. Other hardware and firmware configurations are not yet validated.

## Features

- Original FLSUN UI, captured from the Linux framebuffer.
- Browser clicks translated into touchscreen input events.
- Read-only browser mode by default.
- Local SSH tunnel; no public HTTP listener or mandatory cloud service.
- Python standard library only.
- Optional systemd startup service.
- No firmware flashing or modifications to Klipper, Moonraker or the original TUI.

## Requirements

The printer must already be connected to Wi-Fi or an accessible network, with working SSH credentials and sudo access. The original TUI must still be running. The tested configuration uses Python 3.7, ARMv7 Linux, systemd, /dev/fb0 (480 × 272, 32-bit BGRA, stride 1920), /dev/input/event1 (tlsc6x_touch) and /etc/pointercal. A disconnected display must not prevent these devices from working.

## Installation

See [the installation guide](docs/INSTALLATION.md). The original tested source is [remote_touch_v021.py](remote_touch_v021.py). The supplied installer is new and has not been tested on printer hardware; manual installation is documented as well.

## Safety and limitations

Keep the service bound to 127.0.0.1 and use SSH forwarding only. Never expose port 8765 directly to the network or internet. Anyone with access to the local service can potentially obtain its touch token. The browser's read-only toggle is not a server-side safety interlock. This software can operate real heaters and moving machinery. Test only with the printer idle and cold, stay nearby, and retain access to the physical power switch. Do not rely on the browser for emergency stopping.

Touch coordinates and device numbering are specific to the tested configuration. Verify compatibility before enabling touch. A stale browser page may return HTTP 403 after restarting the service; reload the page or open a fresh private window. Long-term reliability and crash recovery have not been independently validated.

## Roadmap and contributions

This is an ongoing open-source project, not a finished product. Ideas, bug reports and pull requests are welcome. Proposed browser enhancements include fullscreen, adjustable scaling and refresh rate, screenshots, reconnect handling, improved caching and diagnostics, and optional read-only Moonraker statistics. Camera integration and mobile support are exploratory. None of these roadmap features are promised or implemented yet.

Please include your printer model, firmware version, relevant device information and reproducible steps when reporting issues. Remove credentials, tokens and private network information from logs. Keep experimental changes separate from the tested baseline.

Unofficial community project; not affiliated with or endorsed by FLSUN.
