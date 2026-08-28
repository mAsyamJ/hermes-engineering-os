# Phase 4 Implementation Report

Status: **COMPLETE**  
Completed: 2026-08-28  
Product repository: `/opt/hermes-engineering-os`  
Evaluation contract: `phase4-eval-v1`  
Do not start Phase 5 from this report. Do not push.

## Delivered

- Versioned derived evaluation schema on unpublished `hermes_engineering`
  (migration `0002_evaluation`). Phase 3 tables remain valid. Phoenix schema
  unchanged (65 user tables).
- Eligibility engine: historical production without immutable artifacts is
  `INSUFFICIENT_EVIDENCE` and is not scored.
- Immutable artifact capture (`COMMIT_SNAPSHOT`, tracked patch) with secret
  and size guards.
- Sandboxed candidate execution (network none, non-root, no Docker socket,
  no host secrets). Fixture Python evaluators are the qualified toolchain.
- Baseline/candidate comparison: UNCHANGED_PASS / INTRODUCED_FAILURE /
  FIXED_FAILURE / UNCHANGED_FAILURE.
- Quality vector (no canonical 0–100 score). LLM judge interface is DISABLED.
- GET-only `/evaluations*` on existing sidecar `:9120`. Evaluations UI.
- Incremental timer `hermes-eos-evaluate.timer` (lock `420260827`).
- Fixture canaries A/B/C. Historical eligible-only sweep: 0 scored.

## Live state

| Item | Value |
|---|---|
| Engineering OS HEAD | Phase 4 complete on `main` (this report commit). Parent: `fc232b04c3636403f8bfdf5ee4ef1b07b9160619` |
| Dashboard | `127.0.0.1:9119` (dashboard-only restart) |
| Default gateway | PID `2381797` unchanged |
| `rp-friend` | PID `924` unchanged |
| Phoenix | HEALTHY `127.0.0.1:6006` |
| Analytics + Evaluation API | AVAILABLE `127.0.0.1:9120` GET-only; POST 405 |
| `/evaluations` | AVAILABLE `phase4-eval-v1` quality PASS |
| GitHub API | BLOCKED_AUTH (non-blocking) |
| Storage | 23 GiB free, 69% used (≥20 GiB) |
| `hermes_engineering` | 23 user tables |
| Phoenix DB | 65 user tables |

## Coverage

| Metric | Value |
|---|---|
| Production tasks seen | 101 |
| Historically ELIGIBLE | 0 |
| Production evaluated (scored) | 0 |
| INSUFFICIENT_EVIDENCE rows | 103 (101 production + 2 prior fixtures) |
| Fixture canaries | 3 (`t_eval_canary_a/b/c`) |
| VERIFIED_PASS | 0 |
| VERIFIED_FAIL | canary B INTRODUCED_FAILURE (current) |
| PARTIAL | canaries A and C; acceptance UNKNOWN |
| ERROR | 0 |
| Phoenix CODE projection | DEGRADED fail-open; canonical evaluation COMPLETE |

Zero historical quality scores is correct: no stored candidate commit SHA.

## Canaries

| Canary | Task | Tests comparison |
|---|---|---|
| A clean | `t_eval_canary_a` | UNCHANGED_PASS |
| B regression | `t_eval_canary_b` | INTRODUCED_FAILURE |
| C fix | `t_eval_canary_c` | FIXED_FAILURE |

Canary A correlates to fixture trace `3c6a188a33999ef09cf0bc74c2cae76b`. Phoenix `createTraceAnnotations` is fail-open (payload schema / unexpected error); evaluation rows remain COMPLETE in `hermes_engineering`.
No RetroPick commits. No Hermes worker / LLM spend.

## Verification matrix

### PHASE 3 BASELINE

| Item | Result |
|---|---|
| Phase 3 acceptance | PASS |
| phase3-v1 | PASS |
| analytics timer | PASS |
| analytics data quality | PASS |

### CAPABILITY

| Item | Result |
|---|---|
| repository audit | PASS |
| historical evidence coverage | REPORTED |
| eligible historical tasks | 0 |
| insufficient evidence | 103 |

### SEMANTICS / ARTIFACTS / SANDBOX / EVALUATORS

See `docs/EVALUATION_SEMANTICS.md` and `docs/EVALUATION_CAPABILITY_MATRIX.md`.
Fixture build/test/regression/lint/typecheck/architecture/scope/security PASS.
RetroPick/Android Tier C BLOCKED_RESOURCE / BLOCKED_ENVIRONMENT.
Acceptance UNKNOWN. CI BLOCKED_AUTH. LLM judge DISABLED.
Golden expected YAML lives under `tests/evaluation/golden/`.

### CANARIES / HISTORICAL / PIPELINE / RESULTS / ENGINEERING OS

All PASS as tabulated above. No canonical aggregate score.

### FAIL-OPEN / SECURITY / RESOURCE / RECOVERY / PRODUCTION

| Item | Result |
|---|---|
| A sidecar / evaluation DB unavailable | PASS (Hermes AVAILABLE, evaluations DEGRADED) |
| B sandbox runner failure | PASS evaluation ERROR, Hermes unaffected |
| C candidate timeout | PASS bounded (~1s), no stuck process |
| D candidate OOM/resource | PASS bounded docker `--memory 32m` |
| E Phoenix projection outage | PASS canonical COMPLETE, projection DEGRADED |
| F missing artifact | PASS INSUFFICIENT_EVIDENCE |
| G duplicate scheduler | PASS `status=locked` |
| H killed mid-run | PASS 0 orphan runs without summaries |
| I analytics lock isolation | PASS evaluation success while analytics lock held |
| J GitHub BLOCKED_AUTH | PASS non-GitHub evaluators continue |
| fake-secret leakage | PASS |
| candidate isolation | PASS (no sock, no ssh, network none, `--pull never`) |
| storage gate | PASS 23 GiB free |
| backup | PASS `observability-20260828T002751Z` |
| isolated restore | PASS phoenix 65 / hermes_engineering 23 |
| rp-friend / gateways | PASS PIDs 924 / 2381797 |
| RetroPick Git | PASS `a8edf7dd…` |
| RetroPick Docker excl. hermes-eos-* | PASS recorded |
| Phoenix 65 tables | PASS |
| `scripts/verify.sh` | PASS including live Evaluations view |

## Non-blocking leftovers

- GitHub API `BLOCKED_AUTH`
- `DEFAULT_GATEWAY_OTEL=DEFERRED`
- Historical production not evaluable
- RetroPick full CI BLOCKED_RESOURCE
- Rehearsal `markets-api` unhealthy (pre-existing)
- Origin remote exists on Engineering OS git; **nothing pushed**

## Phase 5

Prerequisites and a proposed plan are documented. Phase 5 is **not** started.
