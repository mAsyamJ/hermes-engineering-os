# Evaluation Evidence Model

Canonical store: `hermes_engineering` (derived). Phoenix annotations are
projections. Hermes Kanban remains task truth. Phase 3 outcomes remain
`phase3-v1` facts.

## Lineage

```
task → (optional run) → (optional trace) → artifact hash →
profile@version → evaluator@version → raw result → comparison →
quality vector → optional Phoenix CODE annotation
```

Missing hops render as UNKNOWN / INSUFFICIENT_EVIDENCE, never invented.

## Evidence kinds

- `artifact.content_hash`
- `git.commit` / `git.patch_hash`
- `profile.config_hash`
- `evaluator.impl_hash`
- `command.argv` (from profile only)
- `command.exit` / `command.duration_ms`
- `log.digest` (bounded stdout/stderr, ≤8 KiB stored)
- `phoenix.trace_id` when correlated
- `github.evidence_state`

No task bodies, comment bodies, span IO, tokens, or host secrets.

## Coverage

Report production / eligible / evaluated / insufficient / unsupported
counts. Zeros are valid coverage truth.
