# Hermes Actuation Seam

Audited against live Hermes 0.20.0 / `c0106e50`.

## Worker path

`gateway/kanban_watchers.py` → `dispatch_once` (no `spawn_fn`) →
`claim_task` → `_default_spawn` → `subprocess.Popen` in
`hermes_cli/kanban_db.py`.

`model_override` becomes `-m` / `--provider` only from Kanban columns inside
`_default_spawn`. Writing those columns would make Engineering OS a
pre-dispatch controller. Forbidden.

## Priority A — official pre-spawn plugin/hook

**NOT_FOUND.** `VALID_HOOKS` has observer-only `kanban_task_claimed`
(returns ignored). No `pre_worker_spawn`.

## Priority B — official worker launcher/wrapper

**NOT_FOUND.** `$HERMES_BIN` changes the binary only. Production gateway never
passes `spawn_fn`.

## Priority C — command template / spawn adapter

**NOT_FOUND.** Argv is hardcoded in `_default_spawn`.

## Priority D — isolated upstream-compatible patch

Required. See `HERMES_ACTUATION_UPSTREAM_PATCH.md`.
Live deploy: **not performed**. Status: `READY_PATCH_NOT_DEPLOYED`.

## PAG-2 live isolated patch

See `docs/operations/HERMES_LIVE_PATCH.md`. QUALIFIED against exact live SHA
`c0106e50`. **Not installed at H1.** Production install is H3 via the
hash-locked deploy-tool.

## Rejected approaches

- PATCH Kanban `model_override` / `skills` / `assignee`
- Retarget running workers (argv immutable after Popen)
- Use `kanban_task_claimed` to rewrite spawn
- Use `pre_llm_call` for model routing
- Patch live Hermes on this VPS
- Symlink tricks that write through to production memory
