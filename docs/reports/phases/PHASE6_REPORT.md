# Phase 6 Implementation Report

Status: **COMPLETE**  
Completed: 2026-08-28  
Product repository: `/opt/hermes-engineering-os`  
Experiment contract: `phase6-exp-v1`  
Do not start Phase 7 from this report. Do not push.

## Delivered

- Versioned pre-registered experimentation on unpublished `hermes_engineering`
  (migration `0004_experiments`). Phase 3/4/5 tables remain valid. Phoenix
  schema unchanged (65 user tables). `hermes_engineering` is 46 user tables
  (31 prior + 15 experiment).
- Contract `phase6-exp-v1`: immutable protocols after freeze, HMAC assignment
  `assign-hmac-sha256-v1`, ITT primary analysis `phase6-analysis-v1`, fixed
  horizon, explicit missingness, multi-dimension validity. No WINNER/LOSER.
- Activated treatments: `NONE` (A/A) and `FIXTURE_ARTIFACT` only. PRODUCTION
  scope rejected. `max_llm_calls=0`.
- Qualification (fixture executor, no Hermes inference, no dispatcher tasks):
  - `fixture-aa-v1` → `NO_CLEAR_EFFECT`
  - `fixture-known-effect-v1` → `EVIDENCE_FOR_CANDIDATE` + `FIXTURE_VALIDATION_ONLY`
  - `fixture-paired-v1` → `EVIDENCE_FOR_CANDIDATE` + `FIXTURE_VALIDATION_ONLY`
- Peeking: `--final` before collected planned pairs returns `BLOCKED_HORIZON`.
- Planner never silently shrinks N (`fixture-paired-v1` plan
  `INFEASIBLE_BUDGET` vs registered N=4).
- GET-only `/experiments*` on existing sidecar `:9120`. Experiments UI is
  coverage-first with WHY drilldown. No PROMOTE/DEPLOY/auto-route. POST 405.
- Incremental timer `hermes-eos-experiments.timer` (lock `620260827`). If
  analytics `320260827`, evaluation `420260827`, or performance `520260827`
  is held, the run returns `status=locked`.
- Cohort wall: `eos-phase6-exp` in `excluded_boards`. Phase 5 `production_all`
  remains N=100. Zero `t_exp_*` in production aggregates. Zero PRODUCTION
  protocols. External LLM spend 0.

## Live state

| Item | Value |
|---|---|
| Engineering OS HEAD at Gate 6.0 | `3da784370d37a61f12a2f007de5e6383ffc05d4b` |
| origin/main at Gate 6.0 | same SHA (local==origin PASS) |
| Completion git | local Phase 6 commits, **not pushed** |
| Dashboard | `127.0.0.1:9119` (dashboard-only restart; PID `1265657`, was `1103545`) |
| Default gateway | PID `2381797` unchanged |
| `rp-friend` | PID `924` unchanged |
| Phoenix | HEALTHY `127.0.0.1:6006` |
| Analytics + Evaluation + Performance + Experiments API | AVAILABLE `127.0.0.1:9120` GET-only; POST 405 |
| `/experiments` | AVAILABLE `phase6-exp-v1` quality PASS, 3 protocols |
| `/performance` | AVAILABLE `phase5-perf-v1` |
| `/evaluations` | AVAILABLE `phase4-eval-v1` |
| GitHub API | BLOCKED_AUTH (non-blocking) |
| Storage | 23 GiB free, 69% used (≥20 GiB) |
| `hermes_engineering` | 46 user tables (31 prior + 15 experiment) |
| Phoenix DB | 65 user tables |
| Backup | `observability-20260828T075837Z` |
| Isolated restore | phoenix 65 / hermes_engineering 46 |
| Experiments timer | `hermes-eos-experiments.timer` active |

## Qualification

| Experiment | Conclusion | Notes |
|---|---|---|
| `fixture-aa-v1` | `NO_CLEAR_EFFECT` | identical artifacts; interval includes 0 |
| `fixture-known-effect-v1` | `EVIDENCE_FOR_CANDIDATE` | broken vs clean; `FIXTURE_VALIDATION_ONLY` |
| `fixture-paired-v1` | `EVIDENCE_FOR_CANDIDATE` | independent trees; peeking `BLOCKED_HORIZON` before collection |

Primary metric: `phase4.quality_vector.tests`. Population: ITT. `auto_route=false`.
`promote=false`. LLM calls recorded: 0.

`--recompute` rebuilt current results; assignment hashes were byte-identical
(`d4ec97adec640c5e98e3ccc47fc07eee504fa2a1f0e6db1aed0a56e00ed158fc`).

## Verification matrix

### BASELINE

| Item | Result |
|---|---|
| Phase 5 | PASS (`PHASE5_REPORT.md` COMPLETE; `/performance` AVAILABLE) |
| phase5-perf-v1 | PASS |
| Phase 4 | PASS (`/evaluations` AVAILABLE) |
| phase4-eval-v1 | PASS |
| Phase 3 | PASS |
| phase3-v1 | PASS |
| local == origin | PASS at Gate 6.0 (`3da7843`). Completion commits are local-only and unpushed |

### CONTRACT

| Item | Result |
|---|---|
| phase6-exp-v1 | PASS |
| pre-registration semantics | PASS freeze + hash; mutation rejected |
| primary metric lock | PASS YAML + freeze |
| sample horizon lock | PASS `planned_n` + FIXED horizon |
| analysis lock | PASS `phase6-analysis-v1` / ITT |
| amendment/version semantics | PASS invalidate path; no silent mutate |

### CONFIG IDENTITY

| Item | Result |
|---|---|
| Hermes version | PASS (`fingerprint.hermes_identity`) |
| model identity | NA (V1 fixtures; snapshot keys exist, treatment not activated) |
| profile hash | NA (V1 fixtures) |
| prompt/config hash | NA (V1 fixtures) |
| skill hashes | NA (V1 fixtures) |
| tool config hash | NA (V1 fixtures) |
| environment fingerprint | PASS |
| secret-free snapshot | PASS (`FAKE_PHASE6_SECRET_ABC123` redacted) |

### ISOLATION

| Item | Result |
|---|---|
| workspace isolation | PASS (independent fixture trees; shared path FAIL) |
| memory isolation | PASS (fixtures); BLOCKED_CAPABILITY (agent cognition / shared profile) |
| skill immutability | PASS (V1 does not mutate skills) |
| base repository identity | PASS (RetroPick HEADs unchanged) |
| cross-arm contamination | PASS (detector + fail-open K) |

### ASSIGNMENT

| Item | Result |
|---|---|
| stable seed | PASS |
| deterministic assignment | PASS HMAC `assign-hmac-sha256-v1` |
| balanced assignment | PASS 1:1 |
| blocked assignment | PASS golden |
| paired order randomization | PASS both arms per pair |
| no outcome-informed assignment | PASS assign-before-run; quality check |
| assignment immutable | PASS; `--recompute` hashes unchanged |

### EXPOSURE

| Item | Result |
|---|---|
| assignment vs exposure separated | PASS separate tables |
| fidelity classification | PASS MATCHED / NONCOMPLIANT |
| fallback fixture | PASS |
| ITT assignment preserved | PASS `reassigned=false` |

### SAMPLE PLAN

| Item | Result |
|---|---|
| binary planning | PASS |
| MDE | PASS explicit |
| alpha explicit | PASS 0.05 |
| power explicit | PASS 0.80 |
| budget feasibility | PASS FEASIBLE / INFEASIBLE_BUDGET |
| no silent sample shrink | PASS (`shrunk=false`; paired plan INFEASIBLE vs max_units) |

### STATISTICS

| Item | Result |
|---|---|
| independent binary | PASS Wilson z=1.96 stdlib |
| paired binary | PASS `paired-binary-wilson-v1` |
| effect estimate | PASS |
| uncertainty | PASS interval |
| n=0 handling | PASS golden |
| missing outcomes | PASS explicit missing_n / missing_rate |

### A/A

| Item | Result |
|---|---|
| protocol frozen | PASS |
| assignments | PASS 16 units / 8 pairs |
| collection | PASS |
| analysis | PASS `NO_CLEAR_EFFECT` |
| no false winner semantics | PASS no WINNER/LOSER |

### KNOWN EFFECT

| Item | Result |
|---|---|
| protocol frozen | PASS |
| expected effect recovered | PASS `EVIDENCE_FOR_CANDIDATE` |
| fixture-only classification | PASS `FIXTURE_VALIDATION_ONLY` |

### PAIRED EXPERIMENT

| Item | Result |
|---|---|
| clean independent units | PASS |
| pair identity | PASS |
| execution order | PASS randomized within pair |
| paired analysis | PASS |

### OUTCOME COLLECTION

| Item | Result |
|---|---|
| Phase 3 source | PASS versions recorded |
| Phase 4 source | PASS `phase4.quality_vector.tests` |
| idempotency | PASS collect ON CONFLICT |
| source versions | PASS quality check |

### VALIDITY

| Item | Result |
|---|---|
| protocol integrity | PASS |
| assignment integrity | PASS |
| config integrity | PASS |
| environment integrity | PASS |
| memory isolation | PASS (fixtures); BLOCKED_CAPABILITY (cognition) |
| exposure fidelity | PASS |
| outcome coverage | PASS |
| evaluator compatibility | PASS |

### PEEKING / STOPPING

| Item | Result |
|---|---|
| fixed horizon | PASS |
| premature efficacy blocked | PASS `BLOCKED_HORIZON` live + golden |
| safety guardrail stop | PASS llm_call_count >0 stops; not an efficacy ranking |

### DATA QUALITY

| Item | Result |
|---|---|
| post-outcome assignment rejected | PASS quality SQL |
| arm mutation rejected | PASS |
| primary metric mutation rejected | PASS freeze / loader |
| protocol hash mismatch rejected | PASS |
| double-arm unit rejected | PASS |
| ITT fallback guard | PASS `reassigned=false` |
| config drift detected | PASS fail-open H |
| fixture leakage prevented | PASS production_all N=100; no `t_exp_*` |
| contamination invalidates | PASS isolation + validity |

### FAIL OPEN

| Item | Result |
|---|---|
| experiment DB unavailable | PASS sidecar down → experiments DEGRADED, Hermes AVAILABLE |
| registration kill | PASS status=locked |
| assignment kill | PASS status=locked |
| collector kill | PASS status=locked |
| analysis kill | PASS status=locked |
| Phase 3 unavailable | PASS last-good experiment results retained |
| Phase 4 unavailable | PASS no observations → not confirmatory |
| Phoenix unavailable | PASS derived `/experiments` readable; core PIDs unchanged |
| duplicate controller | PASS lock 620260827 |
| budget exhaustion | PASS INFEASIBLE_BUDGET, N not shrunk |

### SECURITY

| Item | Result |
|---|---|
| fake secret | PASS plant not in dump/API |
| snapshot redaction | PASS |
| arbitrary command injection absent | PASS loader rejects command keys |
| no production credentials | PASS |

### API/UI

| Item | Result |
|---|---|
| Experiments API | PASS `/experiments*` AVAILABLE |
| GET-only | PASS POST 405 |
| Experiments UI | PASS live spec |
| protocol view | PASS |
| progress view | PASS |
| fidelity view | PASS exposures + WHY |
| validity view | PASS WHY |
| WHY drilldown | PASS |
| no deploy control | PASS no PROMOTE/DEPLOY routes |

### RESOURCE

| Item | Result |
|---|---|
| disk | PASS 23 GiB free, 69% used |
| CPU/RAM | PASS ~4.8 GiB available; Nice=10 timer |
| external LLM spend | **0** |

### RECOVERY

| Item | Result |
|---|---|
| backup | PASS `observability-20260828T075837Z` |
| restore | PASS isolated phoenix 65 / hermes_engineering 46 |
| analysis recompute | PASS same conclusions |
| assignment stability after restore | PASS identical assignment hashes |

### PRODUCTION

| Item | Result |
|---|---|
| Hermes core | PASS |
| Kanban | PASS |
| Memory | PASS (untouched) |
| Skills | PASS (untouched) |
| Profiles | PASS (untouched) |
| rp-friend | PASS PID 924 |
| dispatcher | PASS |
| hermes-otel | PASS 13 hooks |
| Phoenix | PASS 65 tables |
| Phase 3 | PASS |
| Phase 4 | PASS |
| Phase 5 | PASS production_all N=100 |
| RetroPick Git | PASS `a8edf7dd…` porcelain 8 (pre-existing) |
| RetroPick Android Git | PASS `e962490d…` porcelain 39 (pre-existing) |
| RetroPick Docker | PASS (`hermes-eos-*` excluded from boundary) |
| production DB/volumes | PASS unpublished Postgres |
| production experiments executed | **NO** |
| `scripts/verification/verify.sh` | PASS including live Experiments view |

No production-critical item is UNKNOWN.

## Reloads performed

1. One `analytics-api` recreate (GET `/experiments*` volume-mounted `/app:ro`).
2. One dashboard-only restart after UI build (`hermes-dashboard.service`
   PID `1103545` → `1265657`).
3. `systemctl --user enable --now hermes-eos-experiments.timer`.

rp-friend and the default gateway were not restarted.

## Non-blocking leftovers

- GitHub API `BLOCKED_AUTH`
- `DEFAULT_GATEWAY_OTEL=DEFERRED`
- Historical production not evaluable; quality/model/skill/trace/cost
  production coverage remains 0 (Phase 5 observational fact)
- RetroPick full CI BLOCKED_RESOURCE
- Rehearsal `markets-api` unhealthy (pre-existing)
- RetroPick porcelain 8 / Android 39 are pre-existing; not repaired
- Origin remote exists on Engineering OS git; **nothing pushed**
- Agent-cognition memory isolation remains `BLOCKED_CAPABILITY` until a
  dedicated empty profile is used; V1 does not enable that path
- `fixture-paired-v1` power plan is `INFEASIBLE_BUDGET` relative to
  `max_units=16`; registered N=4 was used without shrinking planned N

## Phase 7

Prerequisites and a proposed plan are documented in
`docs/reports/phases/PHASE7_PREREQUISITES.md` and `docs/reports/phases/PHASE7_PROPOSED_PLAN.md`.
Phase 7 is **not** started. No auto-routing, no promotion, no causal
production claims.
