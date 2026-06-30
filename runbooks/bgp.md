# BGP Failure Runbook

## Symptoms
- Gateway latency spikes, packet loss rises, or route advertisements flap.
- External prefixes move repeatedly between primary and secondary edge devices.
- Business services may experience partial reachability.

## Checks
1. Inspect BGP neighbor state, hold timers, route dampening, and recent withdraws.
2. Validate upstream reachability and transport health.
3. Compare route tables between active and standby gateways.

## Actions
1. Prefer the stable edge path while investigating.
2. Clear a single BGP session only after confirming the peer and maintenance status.
3. Notify service owners if public reachability is degraded.
