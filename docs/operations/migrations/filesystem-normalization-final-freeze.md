# Filesystem Normalization — Final Freeze Acceptance

**Branch:** `filesystem-normalization`
**Parent:** `97e59871605e144a62c4016aaead29cbc14c2ab5`
**Date:** 2026-09-03 (UTC)

## Purpose

Durable Git checkpoint for the applied filesystem-normalization architecture. This is not a redesign; it freezes the verified layout, clears active stale references, documents compatibility debt, and commits intentional migration work only.

## Gates (verified)

| Gate | Result |
|---|---|
| Unexplained deletions | 0 |
| Broken operational symlinks | 0 |
| Active stale-path references | 0 |
| Python unit tests | 245 OK |
| `bin/agent-os-verify` | PASS |
| `bin/eos-layout-migrate --verify` | PASS |
| `scripts/verification/layout-check.py` | ok |
| Registry / SKILLS.md regen (×2) | deterministic (same sha256) |
| Skills installed | 104 |
| Skill bundles | 8 (`~/.hermes/skill-bundles`) |
| SQLite integrity | ok (state, kanban, projects, verification_evidence) |
| Dashboard | active / HTTP 200 |
| Hermes version | v0.20.0 |
| Hermes core (EOS check) | unmodified (package-lock ignored) |
| Profiles / sessions / memories / cron / Kanban / OTel | intact |
| Secrets scan (commit candidates) | green |
| Push | **not performed** |

## Compatibility debt (transitional)

See [`migration/compatibility.yaml`](../../../migration/compatibility.yaml):

- Agent OS re-export shims (`agent_os/{classify,router,resolver,schema,inventory,generate,ingest_github}.py`)
- `agent_os/plugin/` residual path (live symlink uses `integrations/hermes/plugin`)
- Hermes-root `dashboard.log` / `gateway-starts.log` deferred (Hermes writer)
- Historical report prose may mention obsolete paths (accepted historical)

Each item has reason, risk, priority, and explicit `remove_when` conditions.

## Evidence

- `tests/evidence/layout-migration/final-freeze/`
- `tests/evidence/layout-migration/final-freeze-<timestamp>/FINAL_FREEZE_SUMMARY.json`
- Prior apply acceptance: `tests/evidence/layout-migration/acceptance-20260903T083009Z/`

## Rollback

See [`filesystem-normalization-rollback.md`](filesystem-normalization-rollback.md). Checkpoint branch: `checkpoint/pre-filesystem-normalization`.
