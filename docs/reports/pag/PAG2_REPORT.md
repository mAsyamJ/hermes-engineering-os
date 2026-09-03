# PAG-2 Report

Contract: `par-v1` / `pag1-v1` remain valid. PAG-2 does **not** enable
unrestricted production adaptation. Auto-promote remains absent.

Captured HEAD: local `8652f98` (and later local commits). **Not pushed.**

## Status (live machine)

| Gate | Status |
|---|---|
| PAG2-0 autonomous hardening | PASS |
| H1 four-principal same-SHA cutover | **READY_FOR_HUMAN** — hermes-op exists; cutover/trust/runtime/actuator not done; not faked |
| H2 confirmatory experiment budget | READY_FOR_BUDGET_AUTHORIZATION |
| H3 hash-locked live spawn-transform | NOT_DEPLOYED |
| Real evidence | BLOCKED_BUDGET |
| Production shadow | BLOCKED_EVIDENCE |
| Approval A / one-task canary | BLOCKED_SECURITY_BOUNDARY |
| Production adaptation | DISABLED |

`scripts/verification/verify-operator-boundary.sh` = `READY_FOR_HUMAN` with
`AUTH_AGENT_PASSWORDLESS_ROOT`, `AUTH_NO_HERMES_OP`,
`AUTH_NO_HERMES_RUNTIME`, `AUTH_NO_HERMES_ACTUATOR`,
`AUTH_GATEWAY_RUNS_AS_AGENT`. PASS is impossible until H1.

## Autonomous work already on this tree

- Isolated live patch QUALIFIED at SHA256
  `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4`
  against exact live SHA `c0106e50`. No ThreadPoolExecutor. Production
  tree unpatched.
- Confirmatory freeze `real-model-sol-vs-terra-v2`: 28 pairs / 56 units.
  Protocol hash `fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a`.
  v1 is PILOT_ONLY.
- HARD vs SOFT vs UNAVAILABLE classified; `-Q` does not cap turns;
  `--max-turns` is HARD; per-unit subprocess timeout is HARD.
- Actuator: SO_PEERCRED, caller authority stripped, atomic no-refund
  reservation, 50ms OS socket timeout.
- Deploy-tool: hash-locked; git refs rejected; `install`/`rollback`
  refused for ubuntu (including ubuntu `sudo`). hermes-op `sudo` is the
  principal (`SUDO_USER`). Detached Ed25519 over canonical manifest
  bytes is required and checked against the H1 trust pub. `canonical`
  prints those bytes (no private key). Example/`not-authorizing` nonces
  cannot be installed. Signed payload includes plugin file hashes plus
  `ipc_client_sha256` / `ipc_transport_sha256`. Install/rollback
  `try-reload-or-restart`s the actuator and `affected_units` so the
  running gateways load the spawn-transform; rollback disables
  `eos-actuation`.
- System unit templates in `deploy/pag2/` — not installed.
- `python -m engineering_os.experiments run-real` is wired and fail-closed
  until H2 authorization. 28 pairs cycle the five `real-v1` templates.
  Each unit is Phase-4 evaluated. `analyze-real` persists
  `analysis.json` (`QUALIFIED_CANDIDATE` or `VALID_NO_PROMOTION`) without
  auto-promote. H2 persist is `h2-write-authorization.sh`, not copying
  the example JSON.
- `scripts/deployment/h2-present-budget.sh` / `scripts/deployment/h3-present-deploy.sh` present
  the next human gates. They do not authorize or deploy.
- Fail-closed production operators: `scripts/deployment/pag2-shadow.sh`,
  `scripts/deployment/pag2-canary.sh`, `scripts/deployment/pag2-rollback.sh`. Live CLI uses
  Unix IPC (`transport=ipc`); ubuntu is `BLOCKED_PEER` via SO_PEERCRED.
  hermes-op runtime probe: `scripts/deployment/pag2-as-runtime.sh pag2-probe`
  (SO_PEERCRED / OS-timeout IPC; does not require a confirmatory
  candidate and must not consume exposure). `pag2-shadow` remains
  evidence-gated (`QUALIFIED_CANDIDATE` or `SKIPPED_NO_CANDIDATE`).
  After H1 that probe loads TCB `engineering_os` but reads experiment
  artifacts and the verifier from `/opt` / the protected
  `/usr/local/lib/hermes-eos/scripts` copy — not from a non-existent
  TCB-parent `.runtime` or `scripts` tree.
- H3 install also hash-locks `deploy/pag2/eos-actuation-plugin/` into the
  protected runtime home, copying from the H1 TCB path
  `/usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/` (not
  ubuntu-writable `/opt` after H1). Repo plugin entry does **not** register the
  spawn hook (live ubuntu symlink stays dashboard/OTel only).
- Secret-free backup helper: `scripts/deployment/pag2-backup.sh`. ubuntu writes
  `.runtime/pag2-backup/` only. hermes-op sudo writes
  `/var/backups/hermes-engineering-os/`. ubuntu sudo is refused. Isolated
  restore rehearsal: `scripts/deployment/pag2-restore-rehearsal.sh` (temp dir only; no live DB).
- Read-only gate dashboard: `scripts/deployment/pag2-status.sh`.
- H1 mechanical cutover `scripts/deployment/h1-cutover.sh` refuses ubuntu
  (`SUDO_USER` must be `hermes-op`), stops ubuntu gateways via
  `systemctl --user -M ubuntu@` **before** credential rsync, and copies
  the live venv's resolved uv cpython into the protected tree (not a
  hardcoded patch version). User units are **moved then
  masked** so the mask symlink is not backed up away. rp-friend `plugins`
  is rewritten off the ubuntu absolute symlink. Exact sudoers
  templates are installed by the human sequence. The verifier and
  `h1-postcheck` inspect **ubuntu** sudo/writability/user-units even when
  run from a hermes-op session, so hermes-op recovery `NOPASSWD: ALL`
  cannot block or fake `status=PASS`.
  Sudoers templates: `deploy/pag2/sudoers-hermes-op` and
  `deploy/pag2/sudoers-ubuntu`.
  Missing `.env`/`auth.json` no longer abort cutover after the ubuntu
  gateways have already been stopped.
- H2 persist exists (`write-budget` / `scripts/deployment/h2-write-authorization.sh`)
  and refuses until H1 `status=PASS` plus the exact authorize phrase.
  Live `LLM_BUDGET_AUTHORIZATION` is still absent.
- Canary bind `scripts/deployment/pag2-bind-canary.sh` is hermes-op only and refuses
  ubuntu. It is the missing write of a `maximum_exposure=1` CANARY
  binding into protected actuator state after Approval A.
- Approval A present (`scripts/deployment/pag2-present-approval-a.sh`) emits
  `generate_approval_request` fields plus `canonical_hex`. Status reads
  verify with `consume=False` so they do not burn the nonce. Pretty JSON
  is not the signed payload.
- Persist auto-disable `scripts/deployment/pag2-rollback-persist.sh` is hermes-op
  only; it loads live `state.json` so runtime identity is kept.
- RetroPick `a8edf7dd…` and Android `e962490…` unchanged.

## Stop lines still in force

Do not fake H1 PASS. Do not paste production private keys. Do not apply
the live patch until H3. Do not run paid LLM units until H2. Do not push.
