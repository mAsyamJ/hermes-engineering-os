# Evaluation Recovery

1. Backup: `scripts/observability/observability-db-backup.sh` already dumps all of
   `hermes_engineering`, including Phase 4 tables.
2. Isolated restore: `scripts/observability/observability-db-verify.sh` against a throwaway
   Postgres. Never restore onto the live volume.
3. Recompute: `COMMIT_SNAPSHOT` artifacts can be recreated from SHA + profile +
   evaluator version. Tracked patches may not be recreatable if the workspace is
   gone.

Hermes continues if evaluation tables are dropped.
