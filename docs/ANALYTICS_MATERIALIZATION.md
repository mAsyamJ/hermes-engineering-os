# Analytics Materialization

Command: `scripts/analytics-materialize.sh` (Docker one-shot, writer role).

```text
READ → NORMALIZE → VALIDATE → DERIVE phase3-v1 → TRANSACTIONAL WRITE → CHECKPOINT
```

Flags: `--dry-run` `--task <id>` `--since <unix>` `--backfill` `--canary` `--recompute` `--ruleset phase3-v1` `--json`.

Dry-run never writes. Per-task failures roll back that task only. `pg_try_advisory_lock(320260827)` rejects overlapping runs with `status=locked`.

Checkpoints in `source_checkpoints` are derived cursors, not Kanban state. They advance only after a successful commit.

Idempotency: UPSERT on `(board, task_id)` / `(board, run_id)` / `trace_id`. Unchanged `source_hash` skips writes unless `--recompute`.

Recompute rewrites facts and appends `outcome_history` when outcome, hash, or ruleset changes.
