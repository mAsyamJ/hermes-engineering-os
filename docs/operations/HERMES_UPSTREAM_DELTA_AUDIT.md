# Hermes upstream spawn architecture delta (PAG-1)

Pinned: 2026-08-29 against `NousResearch/hermes-agent` main
`aff5125f8edf5095aef5d3d79bbbb101c95b9413`.

Live Hermes remains `c0106e50e7ecedb3ce34e785d949725dc4e0e457` and is not fetched
or patched. Distance live → this pin: **4412 commits ahead**.

PAG1-0 capture saw `91608eb…`. Main moved during patch qualification to
`23bae43…` then `aff5125…` (gateway turn-hold / i18n). Spawn files were
unchanged; the patch was re-applied and retested.

## Official seams

Searched by behavior and name: `pre_worker_spawn`, `transform_worker_spawn`,
`transform_kanban_worker_spawn`, `spawn_override`, `spawn_transform`,
`before_spawn`, launcher/wrapper, command-template.

**Result: NOT_FOUND.** No official pre-spawn directive exists.

Observer hooks added since live `c0106e50`:

- `on_kanban_worker_spawned` (after spawn_fn returns and PID persist)
- `on_kanban_worker_exited`
- `on_kanban_worker_stale_claim`
- `on_kanban_task_updated`
- `on_kanban_dispatch_tick`

Returns ignored. `has_hook()` short-circuit. Cannot change argv.

`kanban_task_claimed` still fires before spawn; return ignored.

## `_default_spawn` drift versus live

Current upstream still builds argv in `hermes_cli/kanban_db.py` `_default_spawn`
then `subprocess.Popen`. New flags vs live: `--accept-hooks`, optional
`--toolsets`, `--reasoning`. Env pins for board/session/source remain.

That is why the PAR historical patch cannot be applied byte-for-byte.

## Gate PAG1-6

Official safe seam: **NOT_FOUND**. Continue isolated patch port. Do not apply
to live Hermes.
