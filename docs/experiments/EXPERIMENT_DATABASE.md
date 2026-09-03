# Experiment Database

Migration `migrations/analytics/0004_experiments.sql` extends unpublished
`hermes_engineering`. Phoenix is unchanged (65 user tables). Phase 3–5 tables
are referenced, not duplicated.

Tables: contract/definition/protocol snapshots, config/variant snapshots,
units, assignments, exposures, observations, analysis runs, results,
guardrail events, amendments, checkpoints, contamination events, drift events.

Roles remain owner `hermes_engineering`, writer
`hermes_engineering_writer` (DML, no CREATE, no CONNECT to phoenix), reader
SELECT-only. Default privileges from `scripts/analytics/analytics-db-roles.sh` apply.

Advisory lock `620260827`. Overlap with analytics `320260827`, evaluation
`420260827`, or performance `520260827` returns `status=locked`.
