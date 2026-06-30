# Firewall Saturation Runbook

## Symptoms
- Firewall CPU or session table utilization approaches platform limits.
- Latency increases for inspected flows while raw link utilization remains acceptable.
- Deny or threat inspection counters may spike.

## Checks
1. Review top talkers, session table size, packet drops, and policy hit counters.
2. Confirm whether a new rule, inspection profile, or NAT pool change was deployed.
3. Compare active and standby firewall load.

## Actions
1. Move inspection-heavy flows to the standby firewall when safe.
2. Temporarily reduce non-critical deep inspection profiles.
3. Block obvious abusive sources through the perimeter policy workflow.
