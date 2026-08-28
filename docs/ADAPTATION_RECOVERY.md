# Adaptation Recovery

Backup: `scripts/observability-db-backup.sh` dumps `phoenix`,
`hermes_engineering`, and `hermes_control` when present.

Isolated restore: `scripts/observability-db-verify.sh` loads dumps into a
throwaway Postgres container. Never restore over the live volume from this
script.

Restore must preserve policy hashes, approvals, audit rows, rollback targets,
and bindings. Assignment of new candidate units after restore still requires
a current ACTIVE canary binding and a non-engaged kill switch.
