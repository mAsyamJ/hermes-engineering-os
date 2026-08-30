# Real Causal Experiment Result

Protocol: `real-model-sol-vs-terra-v2`  
Class: CONFIRMATORY (v1 is PILOT_ONLY)  
Horizon: 28 pairs / 56 units frozen before any model output  
Protocol hash: `fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a`

**Execution: NOT_EXECUTED.** Status `READY_FOR_BUDGET_AUTHORIZATION`.
`budget.max_llm_calls` in git is 0.

H2 must present HARD LIMITS separately from SOFT-MONITORED and UNAVAILABLE
(`docs/REAL_EXPERIMENT_BUDGET.md`). Reply phrase:

`AUTHORIZE EXPERIMENT fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a WITH THE ABOVE HARD LIMITS`

Do not copy `experiments/templates/LLM_BUDGET_AUTHORIZATION.example.json`.
After H1 `status=PASS` and the exact phrase, persist with
`scripts/h2-write-authorization.sh`.

Present HARD vs SOFT vs UNAVAILABLE with
`scripts/h2-present-budget.sh`. After authorization,
`run-real` then `analyze-real`. This file is not QUALIFIED_CANDIDATE and
not VALID_NO_PROMOTION until those commands finish on this machine.
