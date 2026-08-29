# Production Rollback Result

**Status: NOT_EXECUTED** (no production binding to roll back).

Designed behavior (not yet live-qualified):

- Guardrail FAIL → auto-disable future assignment; do not kill a running worker
  unless a separate emergency path is used.
- Deploy-tool rollback hash is the unpatched `c0106e50` tree.
- Exposure is not refunded after a failed spawn.
- Idempotent disable of a binding is allowed; a new artifact needs a new H3.

Auto-promote is absent.
