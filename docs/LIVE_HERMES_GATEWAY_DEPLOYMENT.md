# Live Hermes Gateway Deployment

H1 copies live SHA `c0106e50e7ecedb3ce34e785d949725dc4e0e457` into
`/usr/lib/hermes-runtime/hermes-agent` **without** spawn-transform.

H3 is the first production introduction of
`patches/hermes/live/0001-worker-spawn-transform-live.patch`
(SHA256 `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4`)
plus the IPC client plugin, via the **protected** copy of
`scripts/hermes-eos-deploy-tool.py`.

Git refs are not a deployment authority. Example manifest:
`deploy/pag2/h3-live-patch.manifest.example.json` — not an authorization.

**Current live production tree: NOT_DEPLOYED.** ubuntu `install` is
rejected by the deploy-tool.
