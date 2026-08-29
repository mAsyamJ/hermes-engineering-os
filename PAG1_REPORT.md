# PAG-1 Production Activation Gate 1 Report

Status: **PAG-1 FRAMEWORK COMPLETE**  
Production adaptation: **DISABLED**  
Completed: 2026-08-29  
Contract: `par-v1` remains valid; PAG-1 contract `pag1-v1`  
Product repository: `/opt/hermes-engineering-os`  
Do not push. Do not begin PAG-2. Do not deploy the live Hermes patch.

PAG-1 is not Phase 8 and does not enable production adaptation.

## Independent statuses (EXAMPLE A)

| Cell | Status |
|---|---|
| PAG-1 framework | COMPLETE |
| Secure human authority | READY_FOR_OPERATOR_BOOTSTRAP |
| Operator boundary verifier | READY_FOR_HUMAN (`AUTH_AGENT_PASSWORDLESS_ROOT`) |
| Approval protocol `approval-ed25519-v1` | PASS (scaffolding; no production private key) |
| Official pre-spawn seam | NOT_FOUND |
| Upstream actuation | READY_FOR_UPSTREAM_SUBMISSION |
| Runtime actuation (live) | READY_PATCH_NOT_DEPLOYED |
| Live Hermes patch | NO |
| Memory isolation harness | READY |
| Real experiment preflight | READY |
| Budget authorization | READY_FOR_BUDGET_AUTHORIZATION |
| Real experiment | READY_FOR_BUDGET_AUTHORIZATION |
| Treatment fidelity | BLOCKED_BUDGET |
| Real causal evidence | BLOCKED_BUDGET |
| Production recommendation | BLOCKED_EVIDENCE |
| PAG-2 readiness | BLOCKED_EVIDENCE_AND_AUTHORITY |
| Production shadow | BLOCKED_EVIDENCE |
| Approval A | BLOCKED_SECURITY_BOUNDARY |
| Canary package | BLOCKED_EVIDENCE |
| Approval B | NOT_EXECUTED |
| Production adaptation | DISABLED |
| Production exposures | 0 |

## BASELINE

| Item | Result |
|---|---|
| PAG1-0 entry freeze | PASS (`docs/PAG1_ENTRY_CHECK.md`, `tests/evidence/pag1-entry-20260829T065945Z.json`) |
| Entry SHA origin/local | `9ebd1781b625094993a23fef6ee28660fe701a59` `docs: publish production readiness report` |
| Phase 1–7 reports | COMPLETE / PASS (historical; not rewritten) |
| PAR framework | COMPLETE (`par-v1`); production adaptation DISABLED |
| Plugin symlink | `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` |
| Sidecar `:9120` | GET `/adaptation/readiness` HTTP 200 |
| POST `/adaptation` | HTTP 405 |
| Phoenix `/healthz` | HTTP 200 |
| `/experiments` | HTTP 200 AVAILABLE |
| `scripts/verify.sh` | PASS (179 unit tests; live Adaptation; `verify-pag1-data.sh` C pin MATCH `aff5125`) |

## PRODUCTION

| Item | Result |
|---|---|
| Production adaptation | DISABLED |
| PRODUCTION policy bundles | 0 |
| PRODUCTION approvals | 0 |
| PRODUCTION current bindings | 0 |
| Fixture TEST canary/shadow | fixture-only; unchanged |
| Canary | NOT_RUN |
| Shadow (production) | BLOCKED_EVIDENCE; not executed |
| Routing change | none |

## AUTHORITY

| Item | Result |
|---|---|
| Verifier | `scripts/verify-operator-boundary.sh` (read-only) |
| Status | READY_FOR_HUMAN |
| Primary reason | AUTH_AGENT_PASSWORDLESS_ROOT |
| Also recorded | AUTH_NO_PROTECTED_ACTUATOR, AUTH_VERIFIER_CODE_WRITABLE, AUTH_PROTECTED_UNIT_WRITABLE (rp-friend unit), AUTH_PUBLIC_TRUST_IDENTITY_ABSENT, AUTH_NO_OPERATOR_PRINCIPAL, AUTH_GITHUB_ADMIN_ON_AGENT |
| `ubuntu` sudo | `(ALL) NOPASSWD: ALL` |
| Human operator bootstrap | not executed |
| Operator package | `.runtime/operator-bootstrap/` (gitignored; PRECHECK / CHECKLIST / POSTCHECK / ROLLBACK) |
| SECURE_AUTHORITY READY | NO — honest cell READY_FOR_OPERATOR_BOOTSTRAP |
| Production Ed25519 private key on VPS | NO |
| Sudoers / SSH / operator account changes | none |

## APPROVAL

| Item | Result |
|---|---|
| `approval-ed25519-v1` | PASS (unit + PAG-1 requalification) |
| Wrong-stage / tampered request | rejected |
| Recommendation binding | `recommendation_id` required in `verify_bindings` |
| TEST HMAC cannot authorize `PRODUCTION_*` | PASS |
| Production authorization without trust root | BLOCKED_SECURITY_BOUNDARY |
| Production private key files | absent |

## UPSTREAM

| Item | Result |
|---|---|
| Official pre-spawn / spawn-transform seam | NOT_FOUND |
| Observer hooks cannot change argv | VERIFIED (`on_kanban_worker_*` after PID persist) |
| Pin file | `provenance/HERMES_PAG1_UPSTREAM.yaml` |
| Pinned SHA | `aff5125f8edf5095aef5d3d79bbbb101c95b9413` (`fix(gateway): document turn-hold commit overshoot + route deferred-notice through i18n`, 2026-08-29T07:32:13Z) |
| Pin vs current main at report | MATCH (re-check at `scripts/verify-pag1-data.sh` C) |
| PAG1-0 capture main | `91608eb20ed1dbd733a84ef305533b4527e83b66` (not rewritten) |
| Intermediate pin | `23bae43cfad6722b5a3b49e782ffc5faaf617c59` |
| Plan-time SHA (stale) | `1d8946b40b9333a7fda81be890be31771a312d4f` |
| Historical PAR patch | `patches/hermes/0001-pre-worker-spawn-hook.patch` |
| Historical PAR patch SHA256 | `35aebcf70c31c78f01479c69faadac7b170ce3614c4565ae9f9a38c73c7d3ef6` |
| PAG-1 patch | `patches/hermes/upstream/0001-worker-spawn-transform.patch` |
| PAG-1 patch SHA256 | `8400003f96942112ec3abfbf9b3d47c47d5bdff044a919fc8327b1f16f8e29de` |
| Hook | `transform_kanban_worker_spawn` |
| Conflict semantics | agree-or-baseline (not last-writer-wins) |
| SpawnOverrides | `model`, `provider`, `skills`, `profile` only |
| Isolated tests | 30 passed on pin `aff5125` (new hook + lifecycle + dispatch lock + session source) |
| Sparse-checkout toolset failures | pre-existing missing `plugins/`; not a patch regression |
| PR package | `docs/HERMES_UPSTREAM_PR_READY.md` |
| Upstream PR / push | NOT submitted |
| Live tree fetch | NOT performed |

## LIVE ACTUATION

| Item | Result |
|---|---|
| Live Hermes path | `/home/ubuntu/.hermes/hermes-agent` |
| Live HEAD | `c0106e50e7ecedb3ce34e785d949725dc4e0e457` |
| `pre_worker_spawn` / `transform_kanban_worker_spawn` in live `kanban_db.py` / `plugins.py` | absent |
| Live patch deployed | NO |
| Distance live → pin | ahead_by 4412 |
| Live dirty | pre-existing `package-lock.json` only (not repaired) |
| rp-friend | PID **924** unchanged since 2026-08-14 |
| Default gateway | PID **2381797** unchanged since 2026-08-26 |
| Dashboard | PID **3357475** after dashboard-only restart (was 2568401) |
| Kanban mutation for routing | none |

## MEMORY

| Item | Result |
|---|---|
| Harness | `memory-snapshot-v1` READY |
| Identical A/B hash | PASS |
| Secret exclusion | PASS (PAG-1 plants in tests/scripts only) |
| Cross-arm isolation | PASS |
| Production memory unchanged | PASS |
| Cleanup | PASS |
| Hash stable | PASS |

## PREFLIGHT

| Item | Result |
|---|---|
| Protocol | `real-model-sol-vs-terra-v1` |
| Contract | `phase6-exp-v1` |
| Scope | BENCHMARK / NON_PRODUCTION |
| Treatment | MODEL only |
| Design | PAIRED, ITT, FIXED horizon |
| Sample | 5 pairs / 10 units |
| Primary metric | `phase4.quality_vector.tests` (id not changed) |
| `_definition_hash` | `92bd21f095784998d4304bfa016c254cdf7b04e38aeb929132860cf40a771cdf` |
| `_execution` | PREPARED |
| `budget.max_llm_calls` | 0 |
| Evaluator profile | `real-v1` |
| All five cases emit FAIL on broken / PASS on golden | PASS |
| `real-v1-refactor` broken tree | repaired before any model call (omitted last addend so unittest FAIL) |
| Control | `openai-codex` / `gpt-5.6-sol` (configured, not invoked) |
| Candidate | `openai-codex` / `gpt-5.6-terra` (configured, not invoked) |

## BUDGET

| Item | Result |
|---|---|
| `.runtime/experiments/LLM_BUDGET_AUTHORIZATION` | ABSENT |
| PAG-1 wrote a valid authorization | NO |
| Request package | `.runtime/experiments/real-model-sol-vs-terra-v1/{BUDGET_REQUEST.md,protocol-hash.txt,planned-execution.json,AUTHORIZATION_TEMPLATE.json}` |
| Generic `yes` rejected | PASS |
| Binding | protocol id/hash, max units/calls, models, scope BENCHMARK\|NON_PRODUCTION, expiry |
| `created_by` containing pag1/automation | rejected |
| Gate | `engineering_os/experiments/budget_gate.py` fail-closed |

## EXPERIMENT

| Item | Result |
|---|---|
| PAG1-16 execution | SKIPPED |
| Executed | NO / NOT_RUN |
| External LLM calls | **0** |
| Hermes invocations | 0 |
| Outcomes / effect estimate | none |
| Conclusion | NOT_RUN |
| Production recommendation generated | NO |
| Production recommendation activated | NO |

## EVIDENCE

| Item | Result |
|---|---|
| Real causal evidence | BLOCKED_BUDGET |
| QUALIFIED | NO |
| Fixture evidence used as production proof | NO |
| `docs/PAG1_CAUSAL_EVIDENCE.md` | BLOCKED_BUDGET |

## PAG-2 BLOCKERS

| Item | Result |
|---|---|
| PAG-2 started | NO |
| Prerequisites | `docs/PAG2_PREREQUISITES.md` |
| Proposed later plan | `docs/PAG2_PROPOSED_PLAN.md` (not authorized) |
| Missing real evidence | BLOCKED_EVIDENCE (`BLOCKED_BUDGET`) |
| Missing bootstrap | BLOCKED_AUTHORITY (`READY_FOR_OPERATOR_BOOTSTRAP`) |
| Combined cell | **BLOCKED_EVIDENCE_AND_AUTHORITY** |
| Shadow used as evidence shortcut | NO |

## SECURITY

| Item | Result |
|---|---|
| Fake-secret leakage outside tests/scripts | PASS (plants not in docs / report / product) |
| Production approval private key | absent |
| Secret-like values in shipped docs/evidence | PASS (`scripts/verify.sh` scan) |
| Dashboard GET-only | PASS |
| POST `/adaptation` | 405 |
| No deploy / approve / use-winner buttons | PASS |
| Authorization artifact not committed | PASS |

## RESOURCES

| Item | Result |
|---|---|
| Root free at report | ~21 GiB, 72% used |
| Gate | ≥20 GiB free and used < 80% |
| RAM | ~4.8 GiB available |
| Isolated clone | `.runtime/hermes-upstream-pag1` (gitignored; deleted after qualification) |
| Isolated pytest target | `.runtime/pag1-pydeps` (not live Hermes venv; deleted after qualification) |
| Pre-mutation backup | `/var/backups/hermes-engineering-os/observability-20260829T042546Z` |
| Post PAG-1 backup | `/var/backups/hermes-engineering-os/observability-20260829T075156Z` |
| Isolated restore | PASS phoenix 65 / engineering 46 / control 18 (live Postgres untouched) |

## INTEGRITY

| Item | Result |
|---|---|
| Phoenix user tables | 65 |
| `hermes_engineering` | 46 |
| `hermes_control` | 18 |
| Postgres host port | unpublished |
| RetroPick Git | `a8edf7dd3e7195aea6f1c826fcf2199ead525162` unchanged |
| Android Git | `e962490dab3ac1072d9ee6371eb1077c0a05c0ac` unchanged |
| RetroPick / Android mutated | NO |
| Documented non-EOS drift | `retropick-markets-rehearsal-markets-api-1` unhealthy ~2 weeks; not repaired |
| EOS timers | analytics, evaluate, performance, experiments, adaptation present |
| Engineering OS / upstream Hermes push | **not pushed** |

## API / UI

| Item | Result |
|---|---|
| GET `/adaptation/readiness` cells | independent; not collapsed |
| Named GET `/adaptation/readiness/{pag2,experiment,upstream}` | 200 |
| POST stays 405 | PASS |
| Dashboard Adaptation view | read-only cells; no deploy/approve |
| Services restarted for PAG-1 | optional `hermes-eos-analytics-api` reload; dashboard-only if UI rebuilt |
| rp-friend / default gateway restart | **none** |

## Reloads performed

1. `hermes-eos-analytics-api` recreate/restart to load GET cell extensions (bind-mount `/opt/hermes-engineering-os:/app:ro`).
2. Dashboard-only restart after Adaptation cell UI rebuild (PID `2568401` → `3357475`).

rp-friend PID **924** and default gateway PID **2381797** were not restarted.

## Production adaptation readiness

**DISABLED.** PAG-1 completed the framework that can advance without production
shadow, live actuation deployment, or canary. Remaining blockers for PAG-2 are
honest: no operator bootstrap, no budget authorization, therefore no real
causal evidence.

## Non-blocking leftovers

- GitHub API remains authenticated with admin on Engineering OS and no branch
  protection. Recorded as AUTH_GITHUB_ADMIN_ON_AGENT; not used as a READY
  authority.
- Live Hermes `origin/main` cache remains stale versus NousResearch main.
  Live tree was not fetched.
- RetroPick porcelain / Android dirty trees remain pre-existing.
- Origin remote exists; **nothing pushed from PAG-1**.
