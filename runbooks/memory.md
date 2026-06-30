# Memory Pressure Runbook

## Symptoms
- Memory utilization rises steadily and does not recover after traffic normalizes.
- Device logs mention allocation failures, route table pressure, or process restarts.
- CPU may rise as garbage collection or route recomputation increases.

## Checks
1. Capture process memory table and platform heap statistics.
2. Confirm whether route scale, NAT sessions, or telemetry subscriptions changed.
3. Compare current memory trend against the last stable baseline.

## Actions
1. Fail over services if redundancy is available.
2. Restart only the leaking process when the platform supports it.
3. If the device remains above 92 percent memory, schedule a controlled reboot.
