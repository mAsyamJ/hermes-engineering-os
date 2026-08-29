# Hermes live spawn-transform patch (PAG-2)

Isolated qualification against exact live SHA
`c0106e50e7ecedb3ce34e785d949725dc4e0e457`. **Not deployed.**

H1 copies this SHA into a protected runtime **without** this patch.
H3 is the first production introduction of the hook + IPC client.

## Artifact

- Isolated worktree (gitignored): `.runtime/hermes-live-pag2`
- Patch: `patches/hermes/live/0001-worker-spawn-transform-live.patch`
- SHA256: `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4`
- Tests: `tests/hermes_cli/test_transform_kanban_worker_spawn_live.py` (6 passed, 2026-08-29)
- Live production tree `/home/ubuntu/.hermes/hermes-agent`: still **unpatched**

## Hook body (production intent)

The isolated live patch adds `transform_kanban_worker_spawn` with
**synchronous** `invoke_hook` (no `ThreadPoolExecutor`). A generic plugin
callback is **not** hard-preemptable: if a plugin never returns, that
worker spawn waits. EOS production use is the thin IPC client in
`engineering_os/adaptation/hermes_plugin.py` which uses
`socket.settimeout` (50ms) and fail-opens to BASELINE. That client is
installed at **H3**, not H1.

The historical PAG-1 upstream patch still uses ThreadPoolExecutor +
`future.result(timeout=)` then `shutdown(wait=True)`. That is **not** a
hard OS timeout of a never-return callback. Do not treat it as one.

## Status

`QUALIFIED` for isolated content-hash deploy via the hash-locked
deploy-tool. `NOT_DEPLOYED` on the live production tree.
