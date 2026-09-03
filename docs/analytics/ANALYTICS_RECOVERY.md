# Analytics Recovery

Two independent recoveries:

1. **Backup restore** — `scripts/observability/observability-db-backup.sh` dumps `phoenix` and `hermes_engineering`. Prove with `scripts/observability/observability-db-verify.sh` against a throwaway container. Never restore onto the live volume.
2. **Source recompute** — delete derived rows or empty `hermes_engineering` public tables and run `scripts/analytics/analytics-materialize.sh --backfill --recompute`. Hermes Kanban, Git, and Phoenix GraphQL remain the sources.

Hermes continues if `hermes_engineering` is dropped.
