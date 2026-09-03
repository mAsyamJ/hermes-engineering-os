# Performance Attribution

Observational association only.

## Model

Preserve provider, model identifier, and source. Do not merge similar names.

- SINGLE_MODEL: exactly one (provider, model) on qualifying runs. Outcome association allowed.
- MIXED_MODEL: two or more. Task outcome stays MIXED_MODEL. Usage-share only.
- UNKNOWN: no `run_model_usage` rows.

Current Hermes profile intended model is **not** historical attribution.

## Profile

Profile **name** is observational metadata. `PROFILE_CONFIG_VERSION = UNKNOWN`
unless an immutable hash was recorded at execution time (it was not).

## Skill

Presence is observational. Multi-skill executions keep every skill. No primary
skill. Language: "associated with", never "caused by."

## Prompt / config

`PROMPT_VERSION_PERFORMANCE = UNSUPPORTED_EVIDENCE` in this deployment.

## Task class

No explicit Kanban labels exist. Titles are not classified by NLP or LLM.
