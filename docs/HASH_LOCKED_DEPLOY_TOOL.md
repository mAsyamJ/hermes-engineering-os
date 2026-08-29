# Hash-locked deploy tool

Production install never uses `git pull` or a mutable ref.

Commands on `scripts/hermes-eos-deploy-tool.py`:

| Command | Who | Effect |
|---|---|---|
| `verify` / `show` | anyone | hash + expiry + nonce; reject `git_ref` |
| `install` / `rollback` | `hermes-op` only | refused for ubuntu; apply path exists only in the protected copy after H1 |

Required manifest fields: `base_runtime_hash`, `artifact_sha256`,
`affected_files`, `affected_units`, `rollback_hash`, `expiry`, `nonce`.

H3 example (not authorizing): `deploy/pag2/h3-live-patch.manifest.example.json`.
