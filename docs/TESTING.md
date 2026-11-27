# Testing — Build 06D

Maintainer-reported Windows results: 25/25 internal self-tests, 17/17 HTTP API tests and 21/21 live regression checklist items (the latter includes confirmation of both automated suites). Historical cumulative records: 249/251, with 54/54 fault-test records tracked separately; these include repeated checks and are not an independent audit.

Run with Python 3.12 (tested on Windows):
```powershell
python remote_touch_v030_dev_build06d.py --self-test
python remote_touch_v030_dev_build06d.py --api-test
python remote_touch_v030_dev_build06d.py --demo
```
The automated tests do not require a printer. API tests cover missing authorization, wrong key, foreign origin/host, valid simulation, replay, Unicode token, coordinates, malformed/non-object JSON, oversized requests, unknown endpoint, physical touch lock, offline eligibility, expiry, concurrent replay and recovery.

For live monitoring, use the existing v0.2.1 framebuffer service and SSH tunnels to local ports 8765 and 7126 (remote Moonraker port 7125). Run with --live and open http://localhost:8766. Verify display, dashboard, demo touch log, read-only reset on reload and rejection of live eligibility during an active print. Never use the legacy touch interface during printing.

Known open checks: meaningful display quality improvement, dynamic speed variation, long-duration reliability, Build 06D-specific connection fault regression and future physical integration.
