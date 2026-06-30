# Router Restart Runbook

## Preconditions
- A restart is approved by the incident commander or automated guardrail.
- Redundant path health is verified.
- Running configuration, process table, route table, and logs are captured.

## Procedure
1. Drain traffic by increasing route preference on the affected router.
2. Confirm no critical flows remain pinned to the device.
3. Restart the affected process first when possible.
4. If full reboot is required, perform controlled reload and monitor adjacency recovery.

## Validation
1. Verify CPU, memory, latency, and packet loss return to baseline.
2. Confirm routing adjacencies are stable.
3. Keep the incident open until five consecutive healthy polling windows complete.
