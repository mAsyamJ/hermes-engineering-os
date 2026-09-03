# Adaptation Database

Isolated database `hermes_control` on the existing unpublished
`hermes-eos-postgres` server. Not phoenix. Not `hermes_engineering`.

Roles: `hermes_control_owner` (DDL), `hermes_control_operator` (DML),
`hermes_control_reader` (SELECT), `hermes_control_resolver` (SELECT on
bindings/bundles/kill-switch only). All control roles are revoked from
phoenix and `hermes_engineering`.

Migration: `migrations/control/0001_adaptation.sql`. Advisory lock
`720260827`. Overlap with Phase 3–6 locks returns `status=locked`.

Tables: contract snapshots, recommendations, immutable policy bundles,
approvals, versioned bindings, kill switch, shadow decisions, rollout
plans, exposures, guardrail events, rollbacks, append-only audit log,
checkpoints.

Dashboard/API use the reader DSN. Operator CLI uses the operator DSN.
The resolver hot path uses the on-disk cache and does not require Postgres.
