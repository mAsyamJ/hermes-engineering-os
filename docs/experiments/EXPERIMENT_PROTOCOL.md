# Experiment Protocol

Trusted definitions live in `experiments/definitions/*.yaml`. Dashboard HTTP
cannot mutate them.

## Pre-registration

`experiment validate` then `experiment preregister` freeze:

- hypothesis and expected direction
- control / candidate snapshots
- experimental unit and design (INDEPENDENT | PAIRED)
- assignment algorithm `assign-hmac-sha256-v1` and seed
- exactly one primary metric
- secondary metrics (exploratory)
- guardrails
- sample plan (planned N, alpha, power, MDE)
- missingness threshold and on_exceed
- analysis population INTENTION_TO_TREAT, FIXED horizon
- budget (`max_llm_calls=0`, `max_external_cost=0`)

The pre-registration hash is SHA-256 of the canonical protocol JSON.

## Amendments

In-place UPDATE of a frozen protocol is REJECTED. An amendment row records
reason, time, and whether outcomes were already observed. Post-outcome
amendment invalidates confirmatory interpretation.

## Scopes

FIXTURE (default) and BENCHMARK are allowed. PRODUCTION is rejected in V1.
