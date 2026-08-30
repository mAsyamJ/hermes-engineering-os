# Hash-locked deploy tool

Production install never uses `git pull` or a mutable ref.

Commands on `scripts/hermes-eos-deploy-tool.py`:

| Command | Who | Effect |
|---|---|---|
| `verify` / `show` | anyone | hash + expiry + nonce; reject `git_ref` |
| `canonical` | anyone | print hex of signed bytes; no private key; does not install |
| `install` / `rollback` | `hermes-op` via `sudo` (`SUDO_USER=hermes-op`) | refused for ubuntu, including `ubuntu sudo`; Ed25519 signature required over canonical manifest bytes; verified against `/etc/hermes-eos/approval-trust.pub`; `git apply` uses `safe.directory`; example/`not-authorizing` nonces are refused |

Required manifest fields: `base_runtime_hash`, `artifact_sha256`,
`affected_files`, `affected_units`, `rollback_hash`, `expiry`, `nonce`.

H3 present-only (does not apply): `scripts/h3-present-deploy.sh`.
H3 example (not authorizing): `deploy/pag2/h3-live-patch.manifest.example.json`.
Copy it, set a unique nonce (must not contain `example` or `not-authorizing`),
run `canonical`, and sign the printed hex **off-VPS**. The example nonce
cannot be installed even if signed. Canonical bytes include `plugin_files`,
`ipc_client_sha256` (`hermes_plugin.py`), and `ipc_transport_sha256`
(`ipc_client.py`). The same install copies hash-locked
`deploy/pag2/eos-actuation-plugin/` from the **protected** H1 copy at
`/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/` into
`/var/lib/hermes-runtime/home/plugins/eos-actuation`. ubuntu `install`
is refused. After H1 the protected deploy-tool must not read that plugin
from agent-writable `/opt`. Install/rollback `systemctl try-reload-or-restart`
the actuator **and** `affected_units` (gateway USR1 in-band) so the
spawn-transform is actually live; rollback also removes `eos-actuation`
from protected `plugins.enabled`. The same signed nonce may be rolled back **once** after install
(`.used` then `.rolled`). Re-install or second rollback requires a new
nonce and a new signature. Git refs are not a deployment authority.
