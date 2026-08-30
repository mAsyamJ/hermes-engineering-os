# Production Canary Result

**Status: NOT_EXECUTED** (BLOCKED_SECURITY_BOUNDARY until H1).

Operator: `scripts/pag2-bind-canary.sh` then `scripts/pag2-as-runtime.sh pag2-canary`
(hermes-op). ubuntu `pag2-canary` is `BLOCKED_PEER`. Requires H1 PASS,
`QUALIFIED_CANDIDATE`, H3 live seam, runtime-bound Approval A, and a
persisted CANARY binding (`maximum_exposure=1`). Missing natural task
uses canary-workload id `pag2-canary-workload-1`. A second unit is
BASELINE; no refund.

`PRODUCTION_FULL` / `PRODUCTION_BOUNDED` remain disabled.
No canary task has been reserved on this machine.
