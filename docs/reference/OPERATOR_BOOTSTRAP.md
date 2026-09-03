# Operator Bootstrap

Human-only. Autonomous agents must not execute these steps.

Order is mandatory. Create new human access first. Never remove current
access first. After PAG-2 H1 the production gateway identity is
`hermes-runtime`, not `ubuntu`.

Four principals (do not collapse):

| Principal | Role | Login |
|---|---|---|
| `hermes-op` | human administrator (sudo, recovery) | yes |
| `hermes-runtime` | production gateway process | **no** |
| `hermes-actuator` | protected IPC actuator | **no** |
| `ubuntu` | Engineering OS / Cursor agent | yes; SSH key kept |

H1 is a **same-SHA security cutover**. Live Hermes stays at
`c0106e50e7ecedb3ce34e785d949725dc4e0e457` with **no**
`transform_kanban_worker_spawn`. Spawn-transform deploy is H3.

Exact copy-paste commands live in gitignored
`.runtime/operator-bootstrap/` (PRECHECK, H1_COMMANDS, CHECKLIST,
POSTCHECK, ROLLBACK). This file is the contract those commands must
satisfy. Read-only machine dashboard: `scripts/deployment/pag2-status.sh`.

## Lockout prevention (every step)

- Keep the original ubuntu SSH session open until hermes-op sudo is proven
  in a **second** session.
- Never edit sudoers from the only remaining admin session.
- Never delete ubuntu's authorized key.
- If gateway cutover fails, restore previous user units from the snapshot
  taken in PRECHECK.

## 1. Create `hermes-op` (human administrator)

- Precondition: existing ubuntu SSH works; you have a second key off-VPS.
- Action: create login user `hermes-op`, install **only** the human SSH
  public key, grant sudo.
- Verification: open a **separate SSH session** as hermes-op. Confirm
  `sudo -n true` succeeds. ubuntu session still works.
- Rollback: delete only `hermes-op`. Do not touch ubuntu.
- Reply in chat is not required until the full H1 sequence finishes.

## 2. Create non-login `hermes-runtime` and `hermes-actuator`

- Precondition: step 1 verified twice.
- Action: `useradd --system --shell /usr/sbin/nologin` for both.
- Verification: `getent passwd` shows four distinct uids; runtime/actuator
  shells are nologin.

## 3. Install public trust, protected verifier, actuator, deploy-tool

- Precondition: four users exist.
- Action: install **public** Ed25519 trust only at
  `/etc/hermes-eos/approval-trust.pub`. Never place the production private
  key on this VPS. Install protected copies of the verifier, SO_PEERCRED
  actuator, hash-locked deploy-tool, `scripts/verification/verify-operator-boundary.sh`,
  `scripts/deployment/pag2-inspect-ubuntu.sh`, and `deploy/pag2/eos-actuation-plugin/`
  under `/usr/local/lib/hermes-eos/` (script at
  `/usr/local/lib/hermes-eos/scripts/verify-operator-boundary.sh`).
  Socket dir `/run/hermes-eos` owned by hermes-actuator, mode 750, group
  hermes-runtime so the runtime can connect and ubuntu cannot.
- Verification: ubuntu cannot write those paths; `rg SO_PEERCRED` on the
  protected actuator file; deploy-tool rejects git refs; verifier reports
  `AUTH_NO_PROTECTED_VERIFIER_SCRIPT` / `AUTH_NO_PROTECTED_PLUGIN_SOURCE`
  until those copies exist.
- Rollback: remove `/etc/hermes-eos` and `/usr/local/lib/hermes-eos`.

## 4. Same-SHA protected runtime copy (no spawn-transform)

- Precondition: live SHA is still `c0106e50…`; live tree still lacks
  `transform_kanban_worker_spawn`.
- Action: copy live source into `/usr/lib/hermes-runtime/hermes-agent`
  at that exact SHA. Copy the live uv cpython into
  `/usr/lib/hermes-runtime/cpython` and retarget the venv interpreter
  there. Do **not** call `python3 -m venv` (system Python is not the
  live Clang 3.11.15). Drop ubuntu-path editable `.pth` finders so
  production cannot import `/home/ubuntu/.hermes/hermes-agent`. Do
  **not** apply `patches/hermes/live/0001-worker-spawn-transform-live.patch`.
- Verification: `git -C /usr/lib/hermes-runtime/hermes-agent rev-parse HEAD`
  equals live SHA; `rg transform_kanban_worker_spawn` is empty; ubuntu
  cannot write the tree.

## 5. HUMAN ACTION REQUIRED — CREDENTIAL MIGRATION

The current gateway reads `HERMES_HOME=/home/ubuntu/.hermes` including
`.env`, `auth.json`, `config.yaml`, profiles, Memory, Skills. A process
running as hermes-runtime cannot use those files without a copy, and
leaving production `HERMES_HOME` agent-writable would fail H1.

- Action: operator copies credential/home material into
  `/var/lib/hermes-runtime/home` using root rsync (no `cat` of secrets,
  no paste into chat, no git). `chown hermes-runtime` and `chmod 750`
  on the tree; `chmod 600` on `.env` / `auth.json`. Do **not** copy
  `plugins/engineering-os` into the production home on H1. Exclude
  rebuildable `.cache` (Playwright, go-build, uv, pnpm); `--exclude cache`
  does not match `.cache`. Do **not** exclude profile homes, kanban,
  sessions, memories, or runtime `node_modules`. Cutover must refuse
  before stopping ubuntu gateways if the destination filesystem cannot
  hold the copy plus a 2G buffer.
- Verification: files exist, ownership is hermes-runtime, ubuntu cannot
  write the directory; do not print contents.
- If this cannot be done without exposing secrets in chat: stop and say
  the gate name. Do not invent credentials.

## 6. System gateway units as `hermes-runtime`

- Precondition: protected tree + migrated home exist.
- Capture before-cutover hashes/argv/env/board/Memory/Skills/Profiles/
  dispatcher/task state (`scripts/maintenance/capture-h1-baseline.sh`).
- Action: install **system** units from `deploy/pag2/` with
  `User=hermes-runtime`. Include Node on PATH (`node_modules` in the
  protected tree; copy `/home/ubuntu/.hermes/node` to
  `/usr/lib/hermes-runtime/node` if present). Do **not** exclude
  `node_modules` from the runtime rsync. `ExecReload=/bin/kill -USR1 $MAINPID`
  (in-band restart, not Python reload). Enable the actuator **socket**
  unit so systemd owns `/run/hermes-eos/actuator.sock` and the process
  inherits `LISTEN_FDS`. **Stop ubuntu user gateways via
  `systemctl --user -M ubuntu@` before** the credential rsync (hermes-op
  `systemctl --user` does not affect ubuntu). Then start system units,
  **move** ubuntu dispatcher unit files out of
  `/home/ubuntu/.config/systemd/user`, **then mask** them. Masking first
  would move the `/dev/null` symlink away and unmask the units.
- Verification: `systemctl show hermes-gateway.service -p User` is
  `hermes-runtime`; MainPID user is hermes-runtime; ubuntu user units
  are masked; board/dispatcher behavior matches the baseline capture.

Copy-paste (from a hermes-op session; ubuntu SSH stays open). Steps A
(hermes-op + sudoers-hermes-op) and C (public trust only) must already
be done:

```bash
sudo /opt/hermes-engineering-os/scripts/deployment/h1-cutover.sh
```

ubuntu `sudo` of that script is refused (`SUDO_USER` must be `hermes-op`).
It does not reduce ubuntu sudo and does not claim PASS.

## 7. Prove hermes-op recovery, then reduce ubuntu sudo

- Precondition: production gateway already runs as hermes-runtime.
- Action: from the hermes-op session, confirm sudo/recovery. Then
  install `deploy/pag2/sudoers-ubuntu` over `/etc/sudoers.d/90-cloud-init-users`
  (after `visudo -c -f`). That file is the live `NOPASSWD:ALL` grant.
  Keep ubuntu SSH.
- Verification: hermes-op still has sudo; ubuntu still logs in;
  `scripts/verification/verify-operator-boundary.sh` status=`PASS`. The verifier
  inspects ubuntu (sudo, writability, user units), not the calling
  principal. hermes-op recovery `NOPASSWD: ALL` is not an agent grant.
  hermes-op IPC probe (no confirmatory candidate required):
  `sudo scripts/deployment/pag2-as-runtime.sh pag2-probe`. Evidence-gated
  `pag2-shadow` waits until `QUALIFIED_CANDIDATE`.
- Rollback: restore sudoers from the copy taken before the edit,
  using the hermes-op session.

## H1 PASS list (all required; do not fake)

- ubuntu no longer has unrestricted root
- ubuntu cannot modify production Hermes executable/runtime
- ubuntu cannot modify gateway service definitions/drop-ins
- ubuntu cannot modify production plugin discovery
- ubuntu cannot replace the future IPC client path
- ubuntu cannot replace the production trust root
- ubuntu cannot replace the actuator
- ubuntu cannot modify protected policy/binding state
- ubuntu cannot invoke protected deployment with an unsigned artifact
- ubuntu cannot connect to the actuator as hermes-runtime (`SO_PEERCRED`)
- production private signing key absent from the VPS
- hermes-runtime cannot replace actuator/trust root
- hermes-actuator cannot rewrite arbitrary Hermes runtime files except
  through the bounded deploy/rollback tool
- hermes-op recovery still works
- production gateway MainPID user is hermes-runtime
- same-SHA cutover preserved baseline behavior
- live production tree still has **no** spawn-transform (H3)
- `scripts/deployment/h1-postcheck.sh` and `scripts/verification/verify-operator-boundary.sh` both print PASS

Reply after machine verification: `OPERATOR BOOTSTRAP COMPLETE` plus
the **public** key fingerprint only.

Privilege-boundary change is outside autonomous execution scope.
