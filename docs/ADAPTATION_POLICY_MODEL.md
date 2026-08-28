# Adaptation Policy Model

Contract: `phase7-adapt-v1`

## Bundle

An immutable policy bundle contains:

- `policy_id`, `policy_version`, `policy_hash`
- `source_recommendation`
- `treatment_dimension`
- `candidate` config snapshot + hash
- `fallback` config snapshot + hash
- structured `selectors`
- `scope`
- `shadow` requirements
- `canary` plan
- `guardrails`
- `rollback` plan (explicit last-known-good)
- `approval` requirements
- `expiry`
- compatible contract versions: `phase3-v1`, `phase4-eval-v1`,
  `phase5-perf-v1`, `phase6-exp-v1`, `phase7-adapt-v1`

`policy_hash` is SHA-256 of canonical JSON (`canonical_dumps`) of the compiled
spec with secrets stripped and volatile timestamps excluded.

Git file bytes must hash-match the stored bundle. Drift disables candidate
exposure.

## Selectors

Constrained declarative schema only:

```yaml
selectors:
  match: ALL   # or ANY
  conditions:
    - field: board          # board | repository_id | profile | task_label | task_class | environment | scope
      op: EQ                # EQ | IN | NOT_IN
      values: ["eos-phase6-exp"]
```

Forbidden: `command`, `shell`, `exec`, `eval`, regex-on-task-text, LLM fields.

## Precedence

1. GLOBAL KILL SWITCH
2. EXPLICIT DENY
3. ROLLBACK / DISABLE
4. SPECIFIC CANARY BINDING
5. SPECIFIC APPROVED POLICY
6. BASELINE HERMES

Same-priority overlap → `POLICY_CONFLICT` → baseline. Never arbitrary choice.

## Bindings

`adaptation_bindings` is the active pointer. It references an immutable
`policy_hash`. Mutation of a live bundle is rejected. Activation, supersession,
and rollback insert a new `binding_version` (optimistic locking / CAS).
