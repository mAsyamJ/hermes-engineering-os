# Real Experiment Plan

Definition: `experiments/definitions/real-model-sol-vs-terra-v1.yaml`  
Contract: `phase6-exp-v1`  
Scope: `BENCHMARK`  
Treatment: `MODEL` only  
Design: `PAIRED`  
Assignment: `assign-hmac-sha256-v1`  
Analysis: ITT, FIXED horizon  
Primary metric: `phase4.quality_vector.tests`  
Sample: 5 pairs (10 unit executions)

Control: `openai-codex` / `gpt-5.6-sol`  
Candidate: `openai-codex` / `gpt-5.6-terra`

Frozen prospectively: model IDs, evaluator profile `real-v1`, memory snapshot
hash (empty/authored M0 at execution time), disposable repository base,
environment fingerprint, guardrails, budget.

This is a real prospective protocol. It is not a fixture validation
conclusion. Execution is gated by LLM budget authorization.
`_execution: PREPARED`. `max_llm_calls: 0` until authorized.
