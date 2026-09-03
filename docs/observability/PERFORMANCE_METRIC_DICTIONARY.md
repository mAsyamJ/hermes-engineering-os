# Performance Metric Dictionary

Contract: **phase5-perf-v1**. See `docs/observability/PERFORMANCE_SEMANTICS.md`.

| metric_id | unit | denominator | numerator | unknown | NA | aggregation | min presentation | uncertainty | comparison | causal |
|---|---|---|---|---|---|---|---|---|---|---|
| lifecycle_completion_rate | proportion | lifecycle in {DONE,NOT_DONE} | DONE | UNKNOWN counted | — | Wilson | INSUFFICIENT if known_n<10 | Wilson 95% | same cohort/ruleset | forbidden |
| verified_success_rate | proportion | verification in {PASS,FAIL} | VERIFIED_SUCCESS | UNKNOWN | NOT_APPLICABLE | Wilson | INSUFFICIENT_DATA if denom 0 | Wilson | same | forbidden |
| first_pass_rate | proportion | first_pass in {PASS,FAIL} | PASS | UNKNOWN | NOT_APPLICABLE | Wilson | known_n | Wilson | same | forbidden |
| retry_rate | proportion | retry_count known | retry_count>0 | null | — | Wilson | known_n | Wilson | same | forbidden |
| rework_rate | proportion | rework in {DETECTED,NOT_DETECTED} | DETECTED | UNKNOWN | — | Wilson | known_n | Wilson | same | forbidden |
| human_intervention_detection_rate | proportion | cohort N | DETECTED | UNKNOWN stays in N | never false | Wilson | coverage required | Wilson | same | forbidden |
| quality_*_pass_rate | proportion | production ELIGIBLE COMPLETE evaluations with known verdict | PASS (or INTRODUCED_FAILURE for regression) | UNKNOWN | NA | Wilson | INSUFFICIENT_DATA if evaluated_n=0 | Wilson | same eval contract | forbidden |
| task_wall_seconds / run_wall_seconds | seconds | non-null clocks | — | missing clock | — | median/IQR | p90 n>=20 p95 n>=40 | distribution | same | forbidden |
| trace_wall_seconds / llm_call_count / tool_call_count / token_total | mixed | non-null trace fields | — | no trace | — | median | same | distribution | same | forbidden |
| cost_known_rate | proportion | cohort | actual cost known | UNKNOWN | — | never estimate prices | INSUFFICIENT_EVIDENCE if 0 | none | n/a | forbidden |

Efficiency without quality is not "better."
