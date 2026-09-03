# Evaluation Database

Same unpublished Postgres (`hermes-eos-postgres`). Database
`hermes_engineering`. Phoenix schema is never modified.

Migration: `migrations/analytics/0002_evaluation.sql` via
`scripts/analytics/analytics-migrate.sh`. Re-run safe.

Tables: profile snapshots, evaluator snapshots, artifacts, runs, results,
comparisons, evidence, summaries, projections, checkpoints.

Roles unchanged: owner `hermes_engineering`, writer DML, reader SELECT.
Writer cannot CONNECT to `phoenix`. Reader cannot write.

Rollback: restore `hermes_engineering.sql` into an isolated container. Never
drop `phoenix`.
