# Hermes Actuation Upstream Patch

Isolated candidate only. **Not deployed to live Hermes.**

- Source: `/home/ubuntu/.hermes/hermes-agent` @ `c0106e50`
- Patch: `patches/hermes/0001-pre-worker-spawn-hook.patch`
- Isolated worktree (gitignored): `.runtime/hermes-dev`

## Behavior

Adds `pre_worker_spawn` to `VALID_HOOKS`. `_default_spawn` invokes it after
argv/env are built and before `Popen`.

Callback receives an immutable task snapshot (id, assignee, board, skills,
model_override, provider_override). It may return optional `SpawnOverrides`:
`model`, `provider`, `skills`, `profile`.

- Timeout or exception → baseline argv/env
- No Kanban write, no network requirement, no DB write
- Running workers remain immutable
- New tasks only

Engineering OS supplies `resolve_spawn_configuration()` as the policy library
the hook may call later. Production actuation stays `DISABLED`.

## Revert

`git apply -R patches/hermes/0001-pre-worker-spawn-hook.patch` in a clone.
Do not apply to live `/home/ubuntu/.hermes/hermes-agent` without a separate
deployment gate.
