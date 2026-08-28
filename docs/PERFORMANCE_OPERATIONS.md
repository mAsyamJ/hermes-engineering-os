# Performance Operations

Refresh: systemd user timer `hermes-eos-performance.timer` every 5 minutes,
oneshot `scripts/performance-materialize.sh --json`. Advisory lock
`520260827`. If analytics (`320260827`) or evaluation (`420260827`) is held,
the run returns `status=locked` and keeps last-good rows.

Disable: `systemctl --user disable --now hermes-eos-performance.timer`.

Manual: `scripts/performance-materialize.sh --dry-run --json` then without
`--dry-run`. `--recompute` rewrites current aggregates.

API: `http://127.0.0.1:9120/performance*` GET-only. Dashboard proxy
`/api/plugins/engineering-os/performance*`.

Performance failure degrades `/performance*` only. Hermes `/health` stays
AVAILABLE. Do not use the Kanban dispatcher or Hermes Cron. Do not restart
rp-friend.
