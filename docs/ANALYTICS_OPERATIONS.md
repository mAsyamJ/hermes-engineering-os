# Analytics Operations

Refresh: systemd user timer `hermes-eos-analytics.timer` every 5 minutes, oneshot `scripts/analytics-materialize.sh --json`.

Disable: `systemctl --user disable --now hermes-eos-analytics.timer`.

Manual: `scripts/analytics-materialize.sh --task <id> --json`.

Explain: `scripts/analytics-explain.sh <task_id> [board]`.

Missed ticks recover by rescanning in-scope boards and skipping unchanged `source_hash` rows. Overlap is blocked by advisory lock. `source_checkpoints` advance only when a run ends with `success` or `partial`.

Analytics failure is fail-open: Hermes, Phoenix, and Engineering OS `/health` stay up; `/analytics*` returns DEGRADED.

Do not use the Kanban dispatcher or Hermes Cron for refresh.
