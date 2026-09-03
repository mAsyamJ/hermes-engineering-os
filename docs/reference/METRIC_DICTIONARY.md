# Metric Dictionary

Ruleset: **phase3-v1**. See `docs/reference/OUTCOME_SEMANTICS.md` for rule IDs.

| Metric | Kind | Definition | Inputs | UNKNOWN | N/A | Fixture | Recompute |
|---|---|---|---|---|---|---|---|
| `lifecycle_state` | derived | DONE / NOT_DONE / UNKNOWN | task.status | unread | — | same | deterministic |
| `verification_state` | derived | PASS / FAIL / UNKNOWN / NOT_APPLICABLE | GitHub CI, typed objective_result | no typed verifier | github null | N/A if disposable | deterministic |
| `final_outcome` | derived | see R6 | lifecycle + verification | lifecycle unread | — | same | history preserved |
| `first_pass_state` | derived | PASS / FAIL / UNKNOWN / NOT_APPLICABLE | first qualifying run | unclassifiable | no qualifying runs | same | deterministic |
| `retry_count` | derived | qualifying failures before first success | qualifying runs | unclassifiable | — | same | deterministic |
| `rework_status` | derived | DETECTED / NOT_DETECTED / UNKNOWN | events | unread events | — | same | deterministic |
| `rework_count` | derived | reopen cycles | events | null if UNKNOWN | — | same | deterministic |
| `human_intervention_state` | derived | DETECTED / UNKNOWN | events + comment authors | no attributable evidence | — | never false | deterministic |
| `task_wall_seconds` | observed/derived | completed_at − started_at | task clocks | missing clock | — | same | deterministic |
| `run_wall_seconds` | derived | sum of qualifying run walls | run clocks | missing clocks | — | same | deterministic |
| `trace_wall_seconds` | observed | max span window | Phoenix | no trace | — | same | deterministic |
| `llm_total_seconds` | observed | sum llm/api span latency | Phoenix | no llm spans | — | same | deterministic |
| `tool_total_seconds` | observed | sum tool span latency | Phoenix | no tool spans | — | same | deterministic |
| `llm_call_count` | observed | llm.* + api.* spans | Phoenix | no trace | — | same | deterministic |
| `tool_call_count` | observed | tool.* spans | Phoenix | no trace | — | same | deterministic |
| `error_count` | observed | ERROR statusCode or error.type | Phoenix | no trace | — | same | deterministic |
| `token_prompt` / `completion` / `total` | observed | span usage attrs | Phoenix | attrs missing | — | same | deterministic |
| `cost_status` | observed | always UNKNOWN in Phase 3 | none | always | — | same | deterministic |
| `model usage rows` | observed | one row per model/provider/source | spans | no models | — | no collapse | deterministic |
| `skill usage rows` | observed | skill spans only | spans | no skill spans | — | task.skills ignored | deterministic |
| `git_evidence_state` | observed | AVAILABLE / NOT_FOUND / UNKNOWN / NOT_APPLICABLE | git rev-parse | no mapping | fixture without git | same | deterministic |
| `github_evidence_state` | observed | AVAILABLE / BLOCKED_AUTH / NOT_FOUND / NOT_APPLICABLE / UNKNOWN | GitHub adapter | transport error | github null | BLOCKED_AUTH live | deterministic |
| `ci_conclusion` | observed | GitHub check rollup | GitHub | BLOCKED_AUTH | no PR | same | deterministic |
| `merge evidence` | observed | merged flag | GitHub | BLOCKED_AUTH | no PR | same | deterministic |
| `production_cohort` | derived | in-scope production board, not excluded | scope yaml | — | fixture | false | deterministic |
| `evidence_grade` | derived | HIGH if task+run+trace; MEDIUM if task+run; LOW otherwise | coverage | — | — | labeled | deterministic |

Coverage metrics (eligible tasks, trace/git/github/verifier coverage, unknown
first-pass, unknown intervention) are Phase 3 products. UNKNOWN rows remain in
the denominator.
