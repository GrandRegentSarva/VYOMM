# High Latency Runbook

## Symptoms
- End-to-end latency exceeds the site baseline by more than 2x.
- Flow records show queueing on a single path.
- Packet loss may remain low until buffers saturate.

## Checks
1. Compare current latency with forecast trend and neighbor telemetry.
2. Inspect link utilization, QoS queues, and interface errors.
3. Validate whether the issue is isolated to one site, region, or upstream provider.

## Actions
1. Prefer a lower latency backup route.
2. Reduce bulk-transfer priority until queues drain.
3. Escalate to transport team if optical power or carrier handoff counters are abnormal.
