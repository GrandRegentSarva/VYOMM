# CPU Saturation Runbook

## Symptoms
- Router or firewall CPU above 90 percent for more than two polling windows.
- Rising control-plane latency and intermittent management timeouts.
- Neighboring devices report queue growth or delayed keepalives.

## Checks
1. Confirm the high CPU is not caused by scheduled maintenance.
2. Inspect process utilization, route churn, ACL hit counters, and interface interrupt rates.
3. Compare affected device telemetry with adjacent routers and firewalls.
4. Check for recent configuration changes or route flaps.

## Actions
1. Shift non-critical traffic to a secondary path.
2. Apply rate limits for noisy management or telemetry sources.
3. Restart the affected daemon only after preserving process and route snapshots.
4. Keep the device under watch for five minutes after recovery.
