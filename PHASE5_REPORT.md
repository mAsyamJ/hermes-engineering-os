# Phase 5 Implementation Report

Status: **COMPLETE**  
Completed: 2026-08-28  
Product repository: `/opt/hermes-engineering-os`  
Performance contract: `phase5-perf-v1`  
Do not start Phase 6 from this report. Do not push.

## Delivered

- Versioned observational performance intelligence on unpublished
  `hermes_engineering` (migration `0003_performance`). Phase 3/4 tables remain
  valid and are queried, not duplicated. Phoenix schema unchanged (65 user
  tables).
- Contract `phase5-perf-v1`: every aggregate stores coverage, known/unknown/NA
  counts, evidence tier, ruleset/eval versions, and `causal=false`.
- Versioned cohorts (`production_all` N=100 after explicit fixture/canary
  exclusion). `math_fixtures` is never the production UI default.
- Stdlib Wilson intervals and quantiles. No SciPy/NumPy. No new pip packages.
- Evidence tiers: NO_DATA / INSUFFICIENT / EXPLORATORY / PROVISIONAL / SUPPORTED.
- Attribution: SINGLE_MODEL / MIXED_MODEL / UNKNOWN; skills preserved; profile
  **name** only (`CONFIG VERSION: UNKNOWN`). Prompt-version performance is
  `UNSUPPORTED_EVIDENCE`.
- Quality production coverage remains 0: rates are `INSUFFICIENT_DATA` with
  `value=null`, not 0%.
- Deterministic failure taxonomy (no LLM). Comparability, confounding, Simpson
  guard, calendar/rolling trends. Insights are templates, not recommendations.
  Ranking is always `null`.
- GET-only `/performance*` on existing sidecar `:9120`. Performance UI is
  coverage-first with WHY drilldown. POST still 405.
- Incremental timer `hermes-eos-performance.timer` (lock `520260827`). If
  analytics `320260827` or evaluation `420260827` is held, the run returns
  `status=locked` and keeps last-good rows.

## Live state

| Item | Value |
|---|---|
| Engineering OS HEAD | Phase 5 complete on `main` (this report commit). Parent: `9a34f481bcd73b2a275f02cd535510b205b76cbd` |
| Dashboard | `127.0.0.1:9119` (dashboard-only restart; PID `1103545`, was `622315`) |
| Default gateway | PID `2381797` unchanged |
| `rp-friend` | PID `924` unchanged |
| Phoenix | HEALTHY `127.0.0.1:6006` |
| Analytics + Evaluation + Performance API | AVAILABLE `127.0.0.1:9120` GET-only; POST 405 |
| `/performance` | AVAILABLE `phase5-perf-v1` quality PASS, violations `[]` |
| `/evaluations` | AVAILABLE `phase4-eval-v1` |
| GitHub API | BLOCKED_AUTH (non-blocking) |
| Storage | 23 GiB free, 69% used (≥20 GiB) |
| `hermes_engineering` | 31 user tables (23 prior + 8 performance) |
| Phoenix DB | 65 user tables |
| Backup | `observability-20260828T061836Z` |
| Isolated restore | phoenix 65 / hermes_engineering 31 |

## Coverage

`task_outcomes.production_cohort` is 101. Performance cohort `production_all`
excludes analytics canary `t_d4cab17a` and evaluation canaries, so **N=100**.
That is intended.

| Metric | Value |
|---|---|
| Production tasks (Phase 5 cohort) | 100 |
| Outcome-covered | 100 |
| First-pass known (PASS+FAIL) | 73 |
| Lifecycle completion | 0.77 SUPPORTED (77/100) |
| Trace-covered production | 0 |
| Model-covered production | 0 |
| Skill-covered production | 0 |
| Quality-evaluated production | 0 |
| Cost-known | 0 |
| Profile name known | 100 |
| Profile config version known | 0 |
| Prompt version known | 0 |
| Current aggregates | 275 |
| Current comparisons | 88 |
| Failure labels | `INSUFFICIENT_EVIDENCE` 100/100, `LIFECYCLE_INCOMPLETE` 23/100 |

Zero production quality, model, skill, trace, and cost rates is correct:
those sources are empty. Phase 5 does not invent 0% quality or a model
leaderboard.

Last success: materialization `f3dabdde-2c32-4527-b1e5-46c43d4a90c8`
(`--recompute` rebuilt Phase 5 from Phase 3/4).

## Verification matrix

### PHASE 3 / PHASE 4 BASELINE

| Item | Result |
|---|---|
| Gate 5.0 | PASS (`docs/PHASE5_ENTRY_CHECK.md`) |
| Phase 3 `phase3-v1` | PASS |
| Phase 4 `phase4-eval-v1` | PASS |
| Analytics + evaluation timers | PASS |
| Phoenix 65 tables | PASS |

### CONTRACT / COHORTS / STATS

| Item | Result |
|---|---|
| `phase5-perf-v1` | PASS |
| Cohort YAML + hash | PASS |
| Fixture/canary exclusion | PASS (`t_eval_canary_*`, `t_d4cab17a`) |
| Wilson z=1.96 stdlib | PASS golden |
| Evidence tiers | PASS |
| Mixed-model guard | PASS (`openai-codex/gpt-5.6-sol` vs `cli/gpt-5.6-sol`) |
| Prompt-version performance | PASS `UNSUPPORTED_EVIDENCE` |
| Quality n=0 not 0% | PASS `INSUFFICIENT_DATA` / `value=null` |

### ENGINE / MATERIALIZER

| Item | Result |
|---|---|
| Dry-run | PASS `evidence/phase5/current-production/dry-run.json` |
| Persist | PASS 275 aggregates / 88 comparisons |
| `--recompute` | PASS same coverage from Phase 3/4 only |
| Failure taxonomy (no LLM) | PASS |
| Comparability / Simpson | PASS golden |
| Insights non-prescriptive | PASS |
| Ranking | PASS `null` |

### FAIL-OPEN / SECURITY / RESOURCE / RECOVERY / PRODUCTION

| Item | Result |
|---|---|
| A sidecar unavailable | PASS Hermes AVAILABLE, performance DEGRADED |
| B lock held / no false checkpoint | PASS `status=locked` |
| C last-good retained | PASS n=275 |
| D Phase 4 absent quality | PASS `INSUFFICIENT_DATA` |
| E Phoenix down derived readable | PASS |
| F GitHub BLOCKED_AUTH non-blocking | PASS |
| G duplicate timer lock | PASS `status=locked` |
| H ruleset mismatch | PASS `NOT_COMPARABLE` |
| I mixed-model not in SINGLE_MODEL | PASS |
| J fixture leakage verifier | PASS |
| Privacy plant | PASS |
| Reader cannot write performance | PASS |
| Writer cannot CONNECT phoenix | PASS |
| Storage gate | PASS 23 GiB free |
| Backup | PASS `observability-20260828T061836Z` |
| Isolated restore | PASS phoenix 65 / hermes_engineering 31 |
| rp-friend / gateways | PASS PIDs 924 / 2381797 |
| RetroPick Git | PASS `a8edf7dd…` porcelain 8 (pre-existing) |
| Android Git | PASS `e962490d…` porcelain 39 (pre-existing) |
| Phoenix 65 tables | PASS |
| `scripts/verify.sh` | PASS including live Performance view |

## Non-blocking leftovers

- GitHub API `BLOCKED_AUTH`
- `DEFAULT_GATEWAY_OTEL=DEFERRED`
- Historical production not evaluable; quality/model/skill/trace/cost
  production coverage remains 0
- RetroPick full CI BLOCKED_RESOURCE
- Rehearsal `markets-api` unhealthy (pre-existing)
- RetroPick porcelain 8 / Android 39 are pre-existing; not repaired
- Origin remote exists on Engineering OS git; **nothing pushed**

## Phase 6

Prerequisites and a proposed plan are documented. Phase 6 is **not** started.
No experiments, no routing, no causal claims.
