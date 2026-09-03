# Analytics Backfill

Scope: `config/analytics-scope.yaml`.

- Production board: `retropick-markets-release`
- Fixture board `eos-phase2-obs` and `.runtime/` workspaces are cohort `fixture`
- Phantom id `t_phase2obs` is Phoenix-only and is not a `task_facts` key

Command: `scripts/analytics/analytics-materialize.sh --backfill --json` in batches of 10.

Historical production tasks without Kanban-stamped traces remain without `trace_facts`. GitHub `BLOCKED_AUTH` yields COMPLETED_UNVERIFIED for DONE tasks, not VERIFIED_FAILURE.
