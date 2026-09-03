# Performance Database

Same unpublished Postgres (`hermes-eos-postgres`). Database
`hermes_engineering`. Phoenix schema is never modified.

Migration: `migrations/analytics/0003_performance.sql` via
`scripts/analytics/analytics-migrate.sh`. Re-run safe.

Tables: contract/cohort/metric snapshots, materialization runs, aggregates,
comparisons, insights, checkpoints.

Phase 3/4 fact tables are reused, not duplicated.

Roles unchanged: owner `hermes_engineering`, writer DML, reader SELECT.
Writer cannot CONNECT to `phoenix`. Reader cannot write.

Rollback: restore `hermes_engineering.sql` into an isolated container. Never
drop `phoenix`.
