# Adaptation Canary

Canary is progressive-delivery safety validation for **already compiled**
policies. It is not a Phase 6 causal experiment.

Default max concurrent candidate executions: **1**. Selection uses stable
HMAC bucketing. V1 executes fixture units through the existing Phase 4
fixture evaluator (`max_llm_calls=0`). No Hermes dispatcher tasks.

Good fixture (clean artifact) → `CANARY_HEALTHY` → promotion **request**.
Bad fixture (broken artifact) → critical guardrail FAIL → auto-disable.

Production canary is disabled.
