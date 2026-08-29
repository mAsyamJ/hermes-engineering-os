# Hermes upstream PR-ready package (PAG-1)

Status: **READY_FOR_UPSTREAM_SUBMISSION**  
Do **not** open or push a NousResearch/hermes-agent PR unless separately authorized.

## Base

- Repository: https://github.com/NousResearch/hermes-agent
- Exact base SHA: `aff5125f8edf5095aef5d3d79bbbb101c95b9413`
- Patch: `patches/hermes/upstream/0001-worker-spawn-transform.patch`
- Historical PAR patch preserved separately: `patches/hermes/0001-pre-worker-spawn-hook.patch`

## Motivation

Kanban worker model/provider/skills/profile cannot be transformed without
writing task columns. Writing `model_override` makes an external controller
of Hermes dispatch. A fail-open spawn transform lets a plugin adjust the
already-built argv without mutating Kanban.

## Problem

`_default_spawn` constructs a fixed argv and Popen. Observer hooks
(`on_kanban_worker_spawned` and friends) fire too late and ignore returns.
There is no official pre-spawn transform.

## Why Kanban mutation is not appropriate

`model_override` / `provider_override` / `skills` columns are durable board
state. Using them for policy routing turns Engineering OS into a pre-dispatch
controller and retargets future workers via the board, not a single spawn.

## API contract

Hook: `transform_kanban_worker_spawn` (transform family).

- After baseline argv/env are fully constructed, before Popen.
- Immutable task snapshot kwargs only (id, assignee, board, skills,
  model_override, provider_override).
- Return `None` or SpawnOverrides: `model`, `provider`, `skills`, `profile`.
- No argv, env dict, or shell string.
- `has_hook()` short-circuit when no subscriber.
- Timeout 50ms, exception, invalid return, or field conflict → baseline.
- Multiple agreeing callbacks merge; disagreement keeps baseline.
- New workers only. Running workers unchanged.
- Must not write Kanban.

## Hook taxonomy rationale

Upstream transforms (`transform_llm_output`, `transform_api_error_classification`)
return values. Observers (`on_kanban_worker_*`) do not. A spawn identity change
is a transform, Kanban-scoped. First-valid-wins would silently drop a second
plugin's field; last-writer-wins (PAR historical patch / `pre_transcription`)
is too ambiguous for spawn. PAG-1 uses agree-or-baseline.

## Fail-open

Hermes keeps baseline argv on any hook failure. Adaptation remains fail-closed
in Engineering OS.

## Security

No arbitrary injection. Skills reject path separators. Profile goes through
`normalize_profile_name` / `resolve_profile_env`. Snapshot omits env secrets.

## Performance

One `has_hook` probe when unused. 50ms timeout when used.

## Backwards compatibility / migration

NONE. No subscriber → byte/semantic baseline.

## Tests

`tests/hermes_cli/test_transform_kanban_worker_spawn.py` plus existing worker
lifecycle / dispatch lock / session source tests (30 passed in isolated
sparse clone after rebase onto `aff5125`). `test_kanban_worker_spawn_toolsets`
failures pre-exist in the sparse checkout (missing plugin tree), not caused
by this patch.

## Example plugin

```python
def register(ctx):
    def transform_kanban_worker_spawn(**kwargs):
        return {"model": "gpt-5.6-terra", "provider": "openai-codex"}
    ctx.register_hook("transform_kanban_worker_spawn", transform_kanban_worker_spawn)
```

## Suggested PR

Title: `feat(kanban): add fail-open transform_kanban_worker_spawn hook`

Body: summarize this document. Note observers still fire after PID persist.
Migration impact: none.

Not submitted by PAG-1.
