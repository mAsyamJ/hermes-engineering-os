# Hermes Actuation Upstream Patch

Isolated candidates only. **Not deployed to live Hermes.**

## Historical PAR patch

- Source: `/home/ubuntu/.hermes/hermes-agent` @ `c0106e50`
- Patch: `patches/hermes/0001-pre-worker-spawn-hook.patch`
- SHA256: `35aebcf70c31c78f01479c69faadac7b170ce3614c4565ae9f9a38c73c7d3ef6`
- Isolated worktree (gitignored): `.runtime/hermes-dev`
- Hook name: `pre_worker_spawn` (last-writer-wins). Kept as historical evidence.

## PAG-1 current-upstream patch

- Base: NousResearch/hermes-agent `aff5125f8edf5095aef5d3d79bbbb101c95b9413`
- Patch: `patches/hermes/upstream/0001-worker-spawn-transform.patch`
- Hook name: `transform_kanban_worker_spawn`
- Conflict: agree-or-baseline (not last-writer-wins)
- Isolated clone (gitignored): `.runtime/hermes-upstream-pag1`

See `docs/HERMES_UPSTREAM_DELTA_AUDIT.md` and `docs/HERMES_UPSTREAM_PR_READY.md`.

Engineering OS supplies `resolve_spawn_configuration()` as the policy library
the hook may call later. Production actuation stays `DISABLED`.

## Revert

Historical: `git apply -R patches/hermes/0001-pre-worker-spawn-hook.patch` in a clone of `c0106e50`.
PAG-1: `git apply -R patches/hermes/upstream/0001-worker-spawn-transform.patch` on `aff5125`.
Live SHA patch: `patches/hermes/live/0001-worker-spawn-transform-live.patch`
(see `docs/HERMES_LIVE_PATCH.md`). Do not apply any of these to live
`/home/ubuntu/.hermes/hermes-agent` without H3. H1 copies the live SHA
**without** the spawn-transform.
