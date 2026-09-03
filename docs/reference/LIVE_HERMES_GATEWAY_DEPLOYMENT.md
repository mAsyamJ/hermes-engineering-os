# Live Hermes Gateway Deployment

H1 copies live SHA `c0106e50e7ecedb3ce34e785d949725dc4e0e457` into
`/usr/lib/hermes-runtime/hermes-agent` **without** spawn-transform.

H3 is the first production introduction of
`patches/hermes/live/0001-worker-spawn-transform-live.patch`
(SHA256 `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4`)
plus hash-locked `deploy/pag2/eos-actuation-plugin/` (copied into the
H1 TCB at `/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin`)
into `/var/lib/hermes-runtime/home/plugins/eos-actuation`, via the **protected**
copy of `scripts/deployment/hermes-eos-deploy-tool.py`. The ubuntu `/opt` plugin
symlink must not register the spawn hook.

Git refs are not a deployment authority. Example manifest:
`deploy/pag2/h3-live-patch.manifest.example.json` — not an authorization.

**Current live production tree: NOT_DEPLOYED.** ubuntu `install` is
rejected by the deploy-tool. H3 present-only: `scripts/deployment/h3-present-deploy.sh`.
Successful hermes-op install also sets `HERMES_EOS_LIVE_PATCH_HASH`,
enables `eos-actuation` in protected `config.yaml`, and
`try-reload-or-restart`s the actuator plus `affected_units` so the
running gateways load the spawn-transform. Rollback clears the hash,
disables the plugin, and reloads the same units. rp-friend production
plugins must resolve to the protected home, not `/home/ubuntu/.hermes/plugins`.
