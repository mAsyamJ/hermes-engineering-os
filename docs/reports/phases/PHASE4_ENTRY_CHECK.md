# Phase 4 Entry Check

Captured: 2026-08-27T23:49:25Z
Snapshot: [tests/evidence/phase4-entry-20260827T234925Z.json](../../../tests/evidence/phase4-entry-20260827T234925Z.json)
Gate 4.0: **PASS**

Do not start evaluation schema or candidate execution from Phase 3 reports
alone. This freeze is the authoritative Phase 4 entry gate.

## Phase 3 freeze

| Check | Evidence | Result |
|---|---|---|
| Engineering OS HEAD | `fc232b04c3636403f8bfdf5ee4ef1b07b9160619` `docs: publish Phase 3 implementation report` | PASS |
| Author / identity | `mAsyamJ <jayanegara.asyam@gmail.com>` | PASS |
| Working tree | clean | PASS |
| Remotes | `origin` → `git@github.com:mAsyamJ/hermes-engineering-os.git`; `main...origin/main` with no ahead/behind | PASS recorded; **do not push** |
| Phase 3 report | COMPLETE `phase3-v1` | PASS |
| Plugin symlink | `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` | PASS |
| Phase 3 verification command | `scripts/verification/verify.sh` last published as PASS | PASS (re-run required at Phase 4 close) |

Phase 3 report claimed `remotes: none`. Live git has `origin`. That is
Engineering OS remote metadata, not RetroPick drift.

## Hermes / Engineering OS runtime

| Check | Evidence | Result |
|---|---|---|
| Engineering OS plugin | enabled with hermes_otel 1.0 and superpowers 6.3.0 | PASS |
| Dashboard | `127.0.0.1:9119` PID `475347` | PASS |
| Default gateway | PID `2381797` active | PASS unchanged vs Phase 2/3 |
| rp-friend | PID `924` | PASS unchanged |
| Production Kanban | `retropick-markets-release` 101 tasks / 122 runs / 0 running | PASS |
| Fixture board | `eos-phase2-obs` still present (`t_d1c34420`, `t_ce5ca4b3`) | PASS |
| Memory / Skills / Profiles | enabled plugins listed above | PASS |
| GitHub API | `BLOCKED_AUTH` | PASS recorded; non-blocking |

## Phase 3 analytics

| Check | Evidence | Result |
|---|---|---|
| `hermes_engineering` | 13 user tables, migration `0001_init` | PASS |
| Outcomes | 103 (101 production + 2 fixture) | PASS |
| Quality | `/coverage` `PASS`, violations `[]` | PASS |
| Incremental timer | `hermes-eos-analytics.timer` active; last success 101 scanned / 0 changed / 0 errors at 23:46:40Z | PASS |
| Analytics API | `127.0.0.1:9120` AVAILABLE GET-only; POST `/summary` → 405 | PASS |
| Analytics UI | view remains mounted (9 views before Phase 4 Evaluations) | PASS |
| Ruleset | `phase3-v1` | PASS |

## Phase 2 observability

| Check | Evidence | Result |
|---|---|---|
| Phoenix | `/healthz` OK `127.0.0.1:6006` image `version-20.4.0` | PASS |
| Observability Postgres | healthy, `PortBindings={"5432/tcp":null}` | PASS |
| Phoenix user tables | 65 | PASS unchanged |
| Fail-open | analytics/Phoenix outage still degrades evidence only | PASS (architecture unchanged) |

## Production boundaries

| Check | Evidence | Result |
|---|---|---|
| `/opt/retropick` HEAD | `a8edf7dd3e7195aea6f1c826fcf2199ead525162` | PASS vs Phase 2/3 |
| `/opt/retropick-android` HEAD | `e962490dab3ac1072d9ee6371eb1077c0a05c0ac` | PASS vs Phase 2/3 |
| Porcelain counts | 8 and 39 (pre-existing; not repaired) | PASS recorded |
| Docker excl. `hermes-eos-*` | rehearsal/dev set unchanged; `markets-api` still unhealthy | PASS recorded |
| Storage | 22.81 GiB free, 68.1% used | PASS (≥20 GiB, <80%) |

## Historical evaluation coverage (truth, not failure)

| Item | Count |
|---|---|
| Production tasks | 101 |
| Stored candidate commit SHA | 0 |
| Git AVAILABLE | 0 |
| Git NOT_FOUND (named branch, null SHA) | 17 |
| Git UNKNOWN (no branch) | 84 |
| Production traces | 0 |
| GitHub AVAILABLE | 0 |
| Structured acceptance criteria | 0 |
| Historically ELIGIBLE for Phase 4 scoring | **0** |

Do not mass-score these rows. Missing evidence is `INSUFFICIENT_EVIDENCE`.

## Gate 4.0 decision

**PASS.** Evaluation schema, artifact capture, and sandboxed candidate
execution are allowed.

Preconditions held:

1. Phase 3 COMPLETE and analytics incremental refresh healthy
2. `hermes_engineering` valid (13 tables, quality PASS)
3. Phase 2 observability HEALTHY; Phoenix 65 tables
4. Engineering OS healthy; plugin APIs GET-only
5. Production Git HEAD, Docker identity excluding `hermes-eos-*`, and rp-friend PID unchanged
6. Root free ≥20 GiB and used <80%
7. No unexplained production drift
8. No Collector / AgentMemory / Graphiti / live LLM judge / Phase 5
