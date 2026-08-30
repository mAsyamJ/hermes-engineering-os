# Real Experiment Budget

Authorization default: **NONE**  
Status: `READY_FOR_BUDGET_AUTHORIZATION`  
Report: `LLM_BUDGET_AUTHORIZATION_REQUIRED`

A generic `yes` file is rejected. The artifact must bind protocol hash, max
units, max LLM calls, control/candidate models, expiry, and
`scope=BENCHMARK|NON_PRODUCTION`. PAG-1/PAG-2 automation cannot be `created_by`.
Authorization binds **HARD** fields only.

v1 (`real-model-sol-vs-terra-v1`, 5 pairs) is **PILOT_ONLY**. Do not treat it
as confirmatory.

## Confirmatory freeze (v2)

Independent of `plan_binary` (see `engineering_os/experiments/paired_power.py`):

| Method | Pairs |
|---|---|
| EOS planner (`plan_binary`, paired) | 25 |
| Connor 1987 (no continuity correction) | 23 |
| Connor + 2/MDE continuity | 28 |
| Smallest n with exact McNemar power ≥ 0.80 | 25 |

**Frozen confirmatory horizon:** `max(...) = 28 pairs / 56 units`.
Protocol: `real-model-sol-vs-terra-v2`. No N change after observing outcomes.

## HARD LIMITS (enforced)

- Max units: 56 (runner will not start unit 57)
- Max Hermes process invocations: 56 (runner will not spawn invocation 57)
- Max wall per unit: 720 seconds (`subprocess.run` timeout on that process)
- Max wall total: 40320 seconds (runner stop before the next unit)
- Max turns per unit: 20 via isolated `hermes chat --max-turns 20` (CLI arg
  beats config/env on live SHA `c0106e50`). Isolated `config.yaml`
  `agent.max_turns: 20` is a second copy. `HERMES_MAX_ITERATIONS=20` is a
  third copy and is **not sufficient alone** (CLI_CONFIG defaults
  `agent.max_turns` to 500, which would win over env). Delegation toolset
  disabled in the isolated home so subagent budgets cannot exceed the parent.
- `-Q` does **not** cap turns.
- Models: `gpt-5.6-sol` (control), `gpt-5.6-terra` (candidate)
- Provider: `openai-codex` (existing OAuth)
- Scope: `BENCHMARK`
- `budget.max_llm_calls` in the checked-in protocol: **0** until H2
- `planned_max_llm_calls`: 56

## SOFT-MONITORED (not HARD)

- Inner Codex/provider HTTP attempts
- Provider SDK retries
- Any turn count we cannot prove Hermes honors beyond `--max-turns`

## UNAVAILABLE

- Token totals
- Dollar cost (Codex OAuth/subscription; this document does not invent a price)

No local/zero-cost LLM is installed. Prepaid quota is not treated as zero cost.

Do not execute until an explicit authorization artifact exists at
`.runtime/experiments/LLM_BUDGET_AUTHORIZATION` after
`HUMAN ACTION REQUIRED — H2`.

## Template reuse (28 pairs / 5 cases)

`real-v1` has five workspace templates. Confirmatory v2 still runs **28
independent pairs / 56 units**. `assignments_from_protocol` cycles the five
templates under unique `pair_id`s (`real-v1-pair-01` … `real-v1-pair-28`).
Each unit is a fresh copytree. That is ITT-on-executions, not 28 unique
repositories.

## CLI (blocked until authorization)

```bash
python -m engineering_os.experiments budget-limits real-model-sol-vs-terra-v2
/opt/hermes-engineering-os/scripts/h2-present-budget.sh
# After H1 PASS and the exact authorize phrase:
/opt/hermes-engineering-os/scripts/h2-write-authorization.sh \
  'YOUR_HUMAN_IDENTITY' '2027-01-01T00:00:00+00:00'
python -m engineering_os.experiments run-real real-model-sol-vs-terra-v2
python -m engineering_os.experiments analyze-real real-model-sol-vs-terra-v2
```

`run-real` is sequential, isolated, and fail-closed without the H2 artifact.
It does not route production Kanban. After each unit the `real-v1` evaluator
records `phase4.quality_vector.tests`. Hermes process status is not the
primary outcome.

```bash
python -m engineering_os.experiments analyze-real real-model-sol-vs-terra-v2
/opt/hermes-engineering-os/scripts/h2-present-budget.sh
```

`analyze-real` is `QUALIFIED_CANDIDATE` only when ITT evidence is for the
candidate and production recommendation eligibility passes. Horizon-complete
`NO_CLEAR_EFFECT` / `EVIDENCE_AGAINST_CANDIDATE` / `INSUFFICIENT_DATA` is
`VALID_NO_PROMOTION`. Do not invent a winner.
