# PAG-1 real experiment preflight

Protocol: `experiments/definitions/real-model-sol-vs-terra-v1.yaml`  
Contract: `phase6-exp-v1`  
`_execution`: PREPARED  
`_definition_hash`: `92bd21f095784998d4304bfa016c254cdf7b04e38aeb929132860cf40a771cdf`

## Frozen prospectively

| Item | Value |
|---|---|
| Scope | BENCHMARK / NON_PRODUCTION |
| Treatment | MODEL only |
| Design | PAIRED |
| Analysis | ITT, FIXED horizon |
| Sample | 5 pairs / 10 units |
| Primary metric | `phase4.quality_vector.tests` |
| Evaluator profile | `real-v1` |
| Control | openai-codex / gpt-5.6-sol |
| Candidate | openai-codex / gpt-5.6-terra |
| `budget.max_llm_calls` | 0 until human authorization |
| Planned max LLM calls | 10 |
| Max turns/unit | 20 |
| Max wall | 7200s |

## Evaluator coverage (before any model call)

All five cases have `broken/` and `golden/` unittest trees. Broken → FAIL,
golden → PASS for `quality_vector.tests`. Includes `real-v1-refactor`. PAG-1
preflight found the broken refactor tree previously passed tests (duplicated
correct totals). `broken/src/right.py` was repaired **before any model call**
so the primary metric can emit FAIL vs PASS. The primary metric id itself
was not changed.

Primary metric is **not** changed after this freeze.

## Provider configuration

Root and rp-friend default to `gpt-5.6-sol` / `openai-codex`. Several other
profiles already default to `gpt-5.6-terra` / `openai-codex`. Codex catalog
lists both model IDs. No model was invoked during preflight. Secrets not
printed.

## Isolation

Memory snapshot harness: READY (`memory-snapshot-v1`). Workspace copies under
experiment runtime, never RetroPick. Environment fingerprint remains the
protocol freeze at execution time.

## Authorization

Default: NONE. PAG-1 did not write `.runtime/experiments/LLM_BUDGET_AUTHORIZATION`.
Request package: `.runtime/experiments/real-model-sol-vs-terra-v1/`.

Gate PAG1-15: **READY_FOR_BUDGET_AUTHORIZATION**. PAG1-16 skipped.
