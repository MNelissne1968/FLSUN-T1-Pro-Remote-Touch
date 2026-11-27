# Safety and limitations

## Build 06E1 update

The virtual bridge is exercised only in offline tests. Tested failures lock the bridge without automatic retry; recovery requires explicit rearm. The mock timeout is 400 ms, not a validated hardware setting. Browser integration and physical integration are pending. The legacy service remains independently interactive.

Build 06D is a monitoring and simulation application. It does not implement physical touch submission. The legacy v0.2.1 service can still inject real input independently and is not protected by the new safety checks.

The eligibility check requires a ready Klipper connection, known idle print state, no pause or active virtual SD job, zero heater targets and power, temperatures at or below 40°C, and zero reported live velocity. Missing or invalid status is rejected. This is a software check, not a hardware interlock.

Simulation uses a per-process API key, local Host/Origin checks, bounded JSON requests and single-use tokens with a three-second lifetime. Concurrent replay was tested. Local processes with access to the service are not a trusted security boundary. Tokens are not per browser tab. Status can change after a check; no atomic hardware guarantee exists.

Bind services to loopback and use SSH forwarding. Never expose these ports publicly. Do not use remote touch as an emergency stop. Keep physical power access available. Future physical tests must be supervised, idle and cold. Do not retry ambiguous physical commands automatically.

Results are maintainer tests on one printer, not a security audit or safety certification. No firmware changes or extra printer packages were required in the reported development tests.
