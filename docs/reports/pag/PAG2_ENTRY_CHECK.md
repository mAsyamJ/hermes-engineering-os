# PAG-2 Entry Check

Captured: 2026-08-29T11:43:20Z
Snapshot: [tests/evidence/pag2-entry-20260829T114320Z.json](../../../tests/evidence/pag2-entry-20260829T114320Z.json)
Contracts: `par-v1`, `pag1-v1` remain valid. PAG-2 is not unrestricted production adaptation.
Gate PAG2-0: **PASS** for autonomous hardening. Human gates H1–H4 remain required before live TCB cutover, budget spend, patched deploy, and canary.

This freeze is the authoritative Production Activation Gate 2 entry check.
It authorizes **local autonomous hardening only**. It does not authorize sudo/SSH
changes, same-SHA cutover, live spawn-transform deploy, paid LLM execution, or
production routing.

## Baseline

| Check | Evidence | Result |
|---|---|---|
| origin/main | `9ebd1781b625094993a23fef6ee28660fe701a59` | PASS recorded |
| local HEAD | `d84e92cd8c92a50907308bca6e0146d4daa05168` `docs: publish PAG-1 report` | PASS expected PAG-1 HEAD |
| local vs origin | ahead 9, behind 0; PAG-1 **not pushed** | PASS recorded; do not push |
| Working tree | CLEAN | PASS |
| Phase 1–7 / PAR / PAG-1 reports | COMPLETE / historical | PASS |
| Production adaptation | DISABLED; exposures 0 | PASS |
| Plugin symlink | `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` | PASS |
| Historical PAR patch SHA256 | `35aebcf70c31c78f01479c69faadac7b170ce3614c4565ae9f9a38c73c7d3ef6` | PASS preserved |
| PAG-1 upstream patch SHA256 | `8400003f96942112ec3abfbf9b3d47c47d5bdff044a919fc8327b1f16f8e29de` | PASS preserved |

## APIs / runtime

| Check | Evidence | Result |
|---|---|---|
| Sidecar `:9120` | HTTP 200 | PASS |
| `/adaptation/readiness` | 200; cells independent; `production_adaptation=DISABLED` | PASS |
| `/experiments` | HTTP 200 | PASS |
| `/adaptation` POST | HTTP 405 | PASS |
| Phoenix `/healthz` | HTTP 200 | PASS |
| Default gateway | PID `2381797` since 2026-08-26 | PASS |
| rp-friend | PID `924` since 2026-08-14; holds `/home/ubuntu/.hermes/kanban/.dispatcher.lock` | PASS dispatcher owner |
| Dashboard | PID `3357475` since 2026-08-29 07:49:59Z | PASS |
| EOS timers | analytics, evaluate, performance, experiments, adaptation | PASS |
| Kanban running | board `retropick-markets-release`: blocked=5 done=78 todo=17 triage=1 running=0 | PASS quiet window |

## Databases / Docker

| Check | Evidence | Result |
|---|---|---|
| EOS postgres | healthy; host port unpublished (`PortBindings` empty) | PASS |
| Production policy bundles / grants / bindings | 0 | PASS |
| Rehearsal `markets-api-1` | unhealthy ~2 weeks | documented non-EOS drift; not repaired |

## Hermes / production Git

| Check | Evidence | Result |
|---|---|---|
| Live Hermes HEAD | `c0106e50e7ecedb3ce34e785d949725dc4e0e457` | PASS |
| Live tree hash (excl. `.git`/`venv`/`node_modules`/`package-lock.json`) | `1f9a1ede37f177f66ec3e0ea9656e7d8acf9ddd1a828b90fd5b51e311429a395` | PASS recorded |
| Live `transform_kanban_worker_spawn` | absent | PASS unpatched |
| Hermes dirty | `package-lock.json` only (pre-existing) | PASS recorded |
| PAG-1 pin | `aff5125f8edf5095aef5d3d79bbbb101c95b9413` | PASS |
| Current Nous `main` (U0) | `9d9f44d63826b18503f44c754e48e1f4f83b3a6e` (11 commits ahead of pin; prompt/desktop/optional-skill; **no** `kanban_db.py` / `plugins.py` spawn changes) | NON_MATERIAL spawn; retain qualified pin; rebase-if-main-moves |
| `/opt/retropick` | `a8edf7dd3e7195aea6f1c826fcf2199ead525162` dirty 8 | PASS unchanged vs PAG-1 |
| `/opt/retropick-android` | `e962490dab3ac1072d9ee6371eb1077c0a05c0ac` dirty 39 | PASS unchanged vs PAG-1 |

## Privilege / TCB inventory (pre-H1)

| Check | Evidence | Result |
|---|---|---|
| Root free | 20.70 GiB (`22222573568`), 72% used | PASS (≥20 GiB, <80%) |
| RAM available | ~5.1 GiB | PASS |
| `ubuntu` sudo | `(ALL) NOPASSWD: ALL` | VERIFIED; H1 required |
| Human users | `ubuntu` only | VERIFIED |
| SSH keys | 1 line (`retropick-ovh-prod`) | VERIFIED |
| Docker group | ubuntu not in docker | VERIFIED |
| Budget authorization | ABSENT | VERIFIED |
| `/etc/hermes-eos` | missing | VERIFIED no TCB yet |
| `/usr/local/lib/hermes-eos` | missing | VERIFIED |
| `hermes-eos-actuator.service` | missing | VERIFIED |
| User gateway units | ubuntu-writable | VERIFIED AUTH_PROTECTED_UNIT_WRITABLE |
| Operator boundary | `READY_FOR_HUMAN` | VERIFIED |
| Production private key | absent | PASS |
| Runtime principal | both gateways run as `ubuntu` | VERIFIED; H1 must switch to `hermes-runtime` |

Agent-writable paths that can influence production spawn (must enter TCB at H1): live Hermes tree/venv; user systemd units/drop-ins; `~/.hermes/plugins`; profile `config.yaml` / `.env`; `.runtime/adaptation` bindings; unit Environment.

## Readiness cells at entry

Independent; not collapsed:

- secure_human_authority: `READY_FOR_OPERATOR_BOOTSTRAP`
- runtime_actuation: `READY_PATCH_NOT_DEPLOYED`
- upstream_actuation: `READY_FOR_UPSTREAM_SUBMISSION`
- memory_isolation: `READY`
- budget_authorization / real_experiment: `READY_FOR_BUDGET_AUTHORIZATION`
- real_causal_evidence / treatment_fidelity: `BLOCKED_BUDGET`
- pag2_readiness: `BLOCKED_EVIDENCE_AND_AUTHORITY`
- production_shadow: `BLOCKED_EVIDENCE`
- approval_a: `BLOCKED_SECURITY_BOUNDARY`
- production_adaptation: `DISABLED`
- auto_promote: false

## Gate PAG2-0 decision

**PASS** for autonomous local work:

1. Adversarial PAG-1 tests and timeout/IPC hardening in isolated trees
2. Independent confirmatory sample-size freeze
3. Actuator/IPC/deploy-tool **code** (not root install)
4. Isolated live-SHA patch qualification (**not** live apply)

Stop lines until the matching human gate:

1. Do not change sudoers/SSH/accounts except via H1 procedure after user action
2. Do not create a production signing private key on this VPS
3. Do not same-SHA cutover or restart production gateways without H1
4. Do not install spawn-transform into production runtime (H3 only)
5. Do not run paid/external LLM experiments without H2
6. Do not push Engineering OS or upstream Hermes
7. Do not mutate RetroPick / Android
8. Do not fake H1 PASS

## Isolated live patch (autonomous, not deployed)

| Check | Evidence | Result |
|---|---|---|
| Isolated worktree | `.runtime/hermes-live-pag2` at `c0106e50` | QUALIFIED |
| Live patch SHA256 | `51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4` | QUALIFIED |
| Isolated tests | 6 passed; synchronous invoke_hook; no ThreadPoolExecutor | QUALIFIED |
| Production tree | `transform_kanban_worker_spawn` absent | NOT_DEPLOYED (H3) |

