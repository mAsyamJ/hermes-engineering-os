# Production Rollback Result

**Status: NOT_EXECUTED** (no production binding to roll back; H1 not PASS).

Operator: `scripts/deployment/pag2-rollback-persist.sh` (hermes-op). ubuntu
`pag2-rollback` cannot persist protected state (`BLOCKED_WRITE` after H1).
Future-only auto-disable (`interrupt_running=false`, `auto_promote=false`).
Does not kill a running worker. Reads live `state.json` so runtime identity
is preserved. Deploy-tool rollback hash is the unpatched `c0106e50` tree.
Exposure is not refunded.
