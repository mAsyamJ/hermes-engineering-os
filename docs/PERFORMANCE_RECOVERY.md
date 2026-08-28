# Performance Recovery

1. Backup: `scripts/observability-db-backup.sh` dumps all of
   `hermes_engineering` including Phase 5 tables.
2. Isolated restore: `scripts/observability-db-verify.sh` against a throwaway
   container. Never restore onto the live volume.
3. Full recompute: `scripts/performance-materialize.sh --recompute --json`
   from Phase 3 + Phase 4 derived facts. Phase 5 has no irreplaceable state.
