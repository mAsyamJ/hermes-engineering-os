# Real Experiment Budget

Authorization default: **NONE**  
Status: `READY_FOR_BUDGET_AUTHORIZATION`  
Report: `LLM_BUDGET_AUTHORIZATION_REQUIRED`

PAG-1 request package (not authorization):
`.runtime/experiments/real-model-sol-vs-terra-v1/`

A generic `yes` file is rejected. The artifact must bind protocol hash, max
units, max LLM calls, control/candidate models, expiry, and
`scope=BENCHMARK|NON_PRODUCTION`. PAG-1 automation cannot be `created_by`.

## Planned (not authorized)

- Units: 10 (5 paired cases)
- Expected max Hermes invocations: 10
- Expected max turns: 20 per unit (upper bound, not measured)
- Provider: `openai-codex` (existing OAuth; not a local model)
- Models: `gpt-5.6-sol` (control), `gpt-5.6-terra` (candidate)
- `budget.max_llm_calls` in the checked-in protocol: **0**
- `planned_max_llm_calls`: 10
- Max wall time: 7200 seconds

Monetary cost cannot be reliably known for Codex OAuth / subscription usage.
This document does not invent a dollar figure.

No local/zero-cost LLM is installed (no Ollama, no llama.cpp). Prepaid or
cloud quota is not treated as zero cost.

Do not execute until an explicit authorization artifact exists at
`.runtime/experiments/LLM_BUDGET_AUTHORIZATION`.
