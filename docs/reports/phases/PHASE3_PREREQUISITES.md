# Phase 3 Prerequisites

Phase 3 (analytics against `hermes_engineering`) must not start until all of
the following remain true:

1. Phase 2 final gate in `PHASE2_REPORT.md` is COMPLETE.
2. Root filesystem has ≥20 GiB free and used < 80%.
3. `hermes_engineering` is still an empty, isolated database on
   `hermes-eos-postgres` (not RetroPick).
4. Phoenix + observability Postgres health is `HEALTHY` or an operator has
   accepted `DEGRADED`.
5. Production RetroPick Git HEAD, Docker identity excluding `hermes-eos-*`,
   and `rp-friend` PID are unchanged from the Phase 2 close snapshot, or
   drift is explicitly accepted.
6. No Collector, AgentMemory, Graphiti, Hivemind, AI Agent Board, or Agent
   Kanban source is introduced as a runtime dependency.

Do not enable destructive Phoenix auto-delete until the supported retention
mechanism is proven. Do not restart `rp-friend` solely to enable analytics.
