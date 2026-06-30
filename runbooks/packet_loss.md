# Packet Loss Runbook

## Symptoms
- Packet loss exceeds 3 percent and correlates with retransmits or application timeouts.
- Interface counters show drops, CRC errors, queue tail drops, or optical instability.
- Latency may spike after loss appears.

## Checks
1. Inspect interface errors on both ends of the link.
2. Compare loss with NetFlow volume and QoS queue depth.
3. Validate optics, cabling, carrier handoff, and recent path changes.

## Actions
1. Route around the lossy link if redundancy exists.
2. Reduce low-priority traffic until loss returns below 1 percent.
3. Replace optics or open a carrier ticket if physical counters continue rising.
