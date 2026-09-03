# Phase 3 Implementation Report

Status: **COMPLETE**  
Completed: 2026-08-27  
Product repository: `/opt/hermes-engineering-os`  
Ruleset: `phase3-v1`  
Do not start Phase 4 from this report. Do not push.

## Delivered

- Derived analytics database `hermes_engineering` on the unpublished
  observability Postgres. Kanban remains canonical. Dropping analytics does
  not affect Hermes.
- Read-only adapters over Hermes SQLite, Phoenix GraphQL (existing client,
  not internal SQL), local Git, and GitHub. `BLOCKED_AUTH` is a first-class
  evidence state.
- Deterministic materializer (`docker compose run` oneshot, writer role)
  with `phase3-v1` outcomes, per-task commits, advisory lock `320260827`,
  idempotent UPSERT, `--recompute`, and checkpoints only after a run ends.
- Historical backfill of 101 production tasks plus 2 fixture canary tasks.
  Fixtures are excluded from the production cohort.
- Read-only analytics sidecar `127.0.0.1:9120` proxied by GET-only
  Engineering OS routes. Analytics UI with coverage, outcomes, and WHY
  drilldown.
- Systemd user timer `hermes-eos-analytics.timer` every 5 minutes.
- Fail-open A–F, privacy (`FAKE_PHASE3_SECRET_ABC123`), isolated backup
  restore of both databases, and source recompute.

## Live state

| Item | Value |
|---|---|
| Engineering OS HEAD before Phase 3 commits | `c6aa362` Phase 2 report |
| Dashboard | `127.0.0.1:9119` PID `475347` (dashboard-only restart; was `5715`) |
| Default gateway | PID `2381797` unchanged |
| `rp-friend` | PID `924` unchanged |
| Phoenix | `HEALTHY` `127.0.0.1:6006` (~406 MiB) |
| Observability Postgres | `HEALTHY`, no host port (~46 MiB) |
| Analytics API | `AVAILABLE` `127.0.0.1:9120` (~24 MiB) |
| `/analytics` | `AVAILABLE` quality `PASS` |
| `/observability` | `AVAILABLE` `fail_open: true` Phoenix `HEALTHY` |
| GitHub API | `BLOCKED_AUTH` (non-blocking) |
| Production Kanban | `retropick-markets-release` 101 tasks / 122 runs / 0 running |
| Storage | 22.82 GiB free, 68.1% used |
| `hermes_engineering` | 13 user tables, ~9 MB; 103 task facts/outcomes |
| Phoenix DB | 65 user tables, 12 MB (unchanged count) |

## Correlation evidence (exact equality)

Canary `t_d1c34420` (`evidence/phase3/canary/correlation.json`):

| Field | Hermes / Phoenix | Analytics |
|---|---|---|
| task | `t_d1c34420` done | `done` |
| run | `2` completed | `run_id` `2` |
| session | `20260827_170441_968c90` | same |
| `otel.trace_id` | `3c6a188a33999ef09cf0bc74c2cae76b` | same |
| outcome | Kanban DONE, no typed verifier | `COMPLETED_UNVERIFIED` `phase3-v1` |

Historical `t_d4cab17a`: `COMPLETED_UNVERIFIED`, GitHub `BLOCKED_AUTH`, no invented PR URL.

Production Kanban SHA256 unchanged:
`fec0d42b18eccc954c5f35fef511afd5bfaed17a370056f29c68a897dc05bf3b`

Fixture Kanban SHA256 unchanged:
`1dba0ee6870ca5017c1b0a06289731954a67d7437adcd932412bfd5daa4f6a2c`

## Coverage (production cohort, 101 eligible)

| Metric | Value |
|---|---|
| Materialized | 103 (101 production + 2 fixture excluded) |
| VERIFIED_SUCCESS | 0 |
| COMPLETED_UNVERIFIED | 78 |
| VERIFIED_FAILURE | 0 |
| INCOMPLETE | 23 |
| UNKNOWN outcome | 0 |
| Git AVAILABLE | 0 (17 NOT_FOUND / 84 UNKNOWN; expected) |
| GitHub AVAILABLE | 0 |
| GitHub BLOCKED_AUTH | 21 |
| Objective verifier PASS | 0 |
| Trace metrics on production | 0 (`DEFAULT_GATEWAY_OTEL=DEFERRED`; historical tasks lack Kanban-stamped traces) |
| Unknown first-pass | 10 |
| Unknown human intervention | 42 |

Zero VERIFIED_SUCCESS is correct: GitHub is `BLOCKED_AUTH` and no
`metadata.objective_result` ∈ {PASS, FAIL} exists. Kanban DONE is not
treated as verified success.

## Refresh

| Mode | Result |
|---|---|
| Dry-run canary | 3 tasks, no writes |
| Canary write | `t_d1c34420`, `t_ce5ca4b3`, `t_d4cab17a` |
| Historical `--backfill` | 101 scanned, 100 changed, 1 unchanged, 0 errors |
| Second backfill | 101 unchanged (idempotent) |
| Timer incremental | 101 scanned, 0 changed, 0 errors (~21s) |
| `--recompute` `t_d1c34420` | same hash/outcome, new `computed_at`, `outcome_history` row |
| Checkpoints | advance only after `success`/`partial` run end |

## Verification matrix

### PHASE 2 BASELINE

| Item | Result |
|---|---|
| Phase 2 acceptance | PASS |
| Canonical task trace correlation | PASS |
| Phoenix | PASS |
| hermes-otel | PASS |

### SOURCE ADAPTERS

| Item | Result |
|---|---|
| Hermes read adapter | PASS |
| Phoenix supported client | PASS (GraphQL, not internal SQL) |
| Git adapter | PASS |
| GitHub adapter | BLOCKED_AUTH |

### SEMANTICS

| Item | Result |
|---|---|
| Outcome ruleset versioned | PASS `phase3-v1` |
| UNKNOWN semantics | PASS |
| NOT_APPLICABLE semantics | PASS |
| Success semantics | PASS (DONE ≠ verified success) |
| First-pass semantics | PASS |
| Retry semantics | PASS |
| Rework semantics | PASS / UNKNOWN_SUPPORTED |
| Human intervention semantics | PASS / UNKNOWN_SUPPORTED (DETECTED or UNKNOWN, never false) |
| Duration semantics | PASS |
| Model usage semantics | PASS |
| Skill usage semantics | PASS (span-only; live production NA — 0 skill spans) |

### DATABASE

| Item | Result |
|---|---|
| Analytics migrations | PASS `0001_init` |
| Schema constraints | PASS |
| Writer least privilege | PASS |
| Reader read-only | PASS |
| Phoenix DB unchanged | PASS 65 user tables |

### MATERIALIZATION

| Item | Result |
|---|---|
| Dry-run | PASS |
| Single-task | PASS |
| Canary | PASS |
| Historical backfill | PASS |
| Incremental refresh | PASS (timer) |
| Checkpoint recovery | PASS (killed run does not advance checkpoints) |
| Idempotency | PASS |
| Recompute | PASS |
| Ruleset lineage | PASS |

### DATA QUALITY

| Item | Result |
|---|---|
| Golden fixture corpus | PASS (14 cases) |
| Duplicate detection | PASS |
| Cross-source integrity | PASS |
| Fixture exclusion | PASS (2 excluded) |
| Evidence coverage | PASS (surfaced, including zeros) |
| Unknown coverage surfaced | PASS |

### OUTCOMES

| Item | Result |
|---|---|
| Lifecycle outcome | PASS |
| Verification outcome | PASS |
| Final outcome | PASS |
| First-pass outcome | PASS |
| Retry count | PASS |
| Rework | UNKNOWN_SUPPORTED |
| Human intervention | UNKNOWN_SUPPORTED |
| LLM call count | PASS (fixture traces; production UNKNOWN) |
| Tool call count | PASS |
| Trace durations | PASS |

### FAIL-OPEN

| Item | Result |
|---|---|
| Analytics DB / sidecar outage | PASS (Hermes `/health` AVAILABLE, `/analytics` DEGRADED) |
| Phoenix outage | PASS (last-good traces retained; Phoenix process not stopped) |
| GitHub outage/auth block | PASS (`COMPLETED_UNVERIFIED`, not failure) |
| Materializer interruption | PASS |
| Duplicate materializer run | PASS (`locked`) |
| Malformed row isolated | PASS (quality FAIL then cleanup) |

### ENGINEERING OS

| Item | Result |
|---|---|
| Analytics API | PASS GET-only; POST 405 |
| Analytics UI | PASS live Playwright 9 views |
| Task drilldown | PASS |
| Task→run→trace navigation | PASS (`t_d1c34420` run 2 / trace `3c6a188a…`) |
| Git drilldown | PASS (UNKNOWN / NOT_FOUND, no fake SHA) |
| GitHub drilldown | BLOCKED_AUTH |
| Degraded-state rendering | PASS |

### SECURITY

| Item | Result |
|---|---|
| Fake-secret leakage | PASS (`FAKE_PHASE3_SECRET_ABC123` absent from DB/API/logs/normalized adapter/git tracked files except the privacy script) |
| Database secrets | PASS (`.env` gitignored mode `0600`) |
| No raw prompt archive | PASS (no task bodies / comment bodies / span IO) |
| No public PostgreSQL | PASS |

### RESOURCE / RECOVERY

| Item | Result |
|---|---|
| Storage gate | PASS 22.82 GiB free, 68.1% used |
| Materialization resource budget | PASS (full incremental ~21s; analytics API ~24 MiB) |
| Analytics backup | PASS `observability-20260827T230803Z` |
| Isolated restore | PASS phoenix 65 tables, hermes_engineering 13 tables |
| Source recompute | PASS |

### PRODUCTION

| Item | Result |
|---|---|
| Hermes core | PASS |
| Kanban | PASS (source hashes unchanged) |
| Memory | PASS |
| Skills | PASS |
| Profiles | PASS |
| All enabled plugins | PASS (see `scripts/verification/verify.sh`) |
| Phoenix | PASS |
| rp-friend | PASS PID 924 |
| RetroPick Git unchanged | PASS vs Phase 2 entry |
| RetroPick Docker unchanged | PASS (`hermes-eos-*` excluded) |
| RetroPick DB/volumes unchanged | PASS |

## Non-blocking leftovers

- GitHub API `BLOCKED_AUTH`
- `DEFAULT_GATEWAY_OTEL=DEFERRED` (no default-gateway restart)
- Historical production tasks lack Kanban-stamped traces; cost always UNKNOWN
- Rehearsal `markets-api` unhealthy (pre-existing)
- Hermes source `package-lock.json` dirty (do not repair)

## Production invariants held

- No RetroPick source edits; Git HEAD unchanged
- No restart of `hermes-gateway` or `hermes-gateway-rp-friend`
- No Collector, AgentMemory, Graphiti, Phase 4 evaluator
- Postgres unpublished; analytics on Docker network `hermes-eos-observability`
- Plugin APIs remain GET-only
- Nothing pushed

## Phase 4

Prerequisites and a proposed plan are documented. Phase 4 is **not** started.
