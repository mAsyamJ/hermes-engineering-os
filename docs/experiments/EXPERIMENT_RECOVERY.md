# Experiment Recovery

1. Backup: `scripts/observability/observability-db-backup.sh` dumps all of
   `hermes_engineering`, including Phase 6 tables.
2. Isolated restore: `scripts/observability/observability-db-verify.sh` against a throwaway
   container. Never restore onto the live volume.
3. Analysis `--recompute` rebuilds results from frozen protocol, assignments,
   exposures, and observations. Assignment hashes must not change.
4. Pre-registration hashes survive restore.
5. If the experiment layer is dropped, Hermes, Phase 3, Phase 4, and Phase 5
   remain intact.
