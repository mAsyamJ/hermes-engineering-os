# PAG-1 Entry Check

Captured: 2026-08-29T06:59:45Z
Snapshot: [tests/evidence/pag1-entry-20260829T065945Z.json](../../../tests/evidence/pag1-entry-20260829T065945Z.json)
Contract: `par-v1` remains valid. PAG-1 is not Phase 8.
Gate PAG1-0: **PASS**

This freeze is the authoritative Production Activation Gate 1 entry check.
It does not authorize production routing, live Hermes core patches, sudo
changes, operator bootstrap, or paid LLM execution.

## Baseline

| Check | Evidence | Result |
|---|---|---|
| origin/main | `9ebd1781b625094993a23fef6ee28660fe701a59` `docs: publish production readiness report` | PASS |
| local HEAD | same SHA | PASS |
| local == origin | ahead 0 behind 0 | PASS |
| Working tree | CLEAN | PASS |
| Phase 1 report | PASS | PASS |
| Phase 2–7 reports | COMPLETE | PASS |
| PAR framework | COMPLETE (`par-v1`); production adaptation DISABLED | PASS |
| Production exposures | 0 PRODUCTION policy bundles; 0 PRODUCTION approvals; 0 PRODUCTION current bindings | PASS |
| Plugin symlink | `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` | PASS |
| Historical PAR patch | SHA256 `35aebcf70c31c78f01479c69faadac7b170ce3614c4565ae9f9a38c73c7d3ef6` | PASS preserved |

## APIs / runtime

| Check | Evidence | Result |
|---|---|---|
| Sidecar `:9120` health | HTTP 200 | PASS |
| `/adaptation/readiness` | HTTP 200; `production_adaptation=DISABLED`; cells independent | PASS |
| `/experiments` | HTTP 200 | PASS |
| `/adaptation` POST | HTTP 405 | PASS |
| Phoenix `/healthz` | HTTP 200 | PASS |
| Default gateway | PID `2381797` active since 2026-08-26 | PASS unchanged |
| rp-friend | PID `924` active since 2026-08-14 | PASS unchanged |
| Dashboard | PID `2568401` active | PASS |
| EOS timers | analytics, evaluate, performance, experiments, adaptation | PASS |
| Kanban running tasks | none on `retropick-markets-release` | PASS |

## Databases

| Check | Evidence | Result |
|---|---|---|
| Phoenix user tables | 65 | PASS |
| `hermes_engineering` | 46 | PASS |
| `hermes_control` | 18 (PAR completion count; PAR-0 freeze was 14 before PAR migrations) | PASS |
| Postgres host port | unpublished (`5432/tcp: null`) | PASS |

## Hermes / production Git

| Check | Evidence | Result |
|---|---|---|
| Hermes source HEAD | `c0106e50e7ecedb3ce34e785d949725dc4e0e457` | PASS |
| Live `pre_worker_spawn` | NOT present | PASS unpatched |
| Hermes dirty | `package-lock.json` only (pre-existing; not repaired) | PASS recorded |
| `/opt/retropick` HEAD | `a8edf7dd3e7195aea6f1c826fcf2199ead525162` | PASS unchanged |
| `/opt/retropick-android` HEAD | `e962490dab3ac1072d9ee6371eb1077c0a05c0ac` | PASS unchanged |
| Porcelain | RetroPick 8 / Android 39 dirty paths pre-existing; not repaired | PASS recorded |

## Resources / privilege

| Check | Evidence | Result |
|---|---|---|
| Root free | 21.15 GiB (`22704574464` bytes), 71% used | PASS (≥20 GiB, <80%) |
| `ubuntu` sudo | `(ALL) NOPASSWD: ALL` | VERIFIED (not a PAG1-0 failure) |
| Human users | `ubuntu` only | VERIFIED bootstrap not done |
| SSH keys | 1 authorized_keys line | VERIFIED |
| Docker group | ubuntu not in docker; Docker via sudo | VERIFIED |
| Budget authorization | `.runtime/experiments/LLM_BUDGET_AUTHORIZATION` absent | VERIFIED |

## Documented non-EOS drift (not a PAG1-0 failure)

- `retropick-markets-rehearsal-markets-api-1` unhealthy for ~2 weeks. Pre-existing rehearsal stack; not an Engineering OS mutation; not repaired by PAG-1.
- Live Hermes `origin/main` cache is stale versus current NousResearch main. Live tree is not fetched.

## Current upstream at PAG1-0 capture

NousResearch/hermes-agent `refs/heads/main` at capture time:

`91608eb20ed1dbd733a84ef305533b4527e83b66`

This is **newer** than the SHA observed while authoring the PAG-1 plan
(`1d8946b40b9333a7fda81be890be31771a312d4f`). PAG-1 pinned the SHA
fetched at patch freeze, not the plan-time SHA. Live Hermes remains
`c0106e50` and is not updated.

Patch freeze later re-pinned through `23bae43…` to
`aff5125f8edf5095aef5d3d79bbbb101c95b9413` after main moved during
qualification (spawn files unchanged). This entry capture SHA is not rewritten.

## Gate PAG1-0 decision

**PASS.** Safe autonomous PAG-1 work may proceed. Stop lines remain in force:

1. Do not change sudoers, SSH, or operator accounts
2. Do not create a production signing private key on this VPS
3. Do not deploy a Hermes core patch to live runtime
4. Do not run paid/external LLM experiments without a pre-existing valid authorization artifact
5. Do not create that budget authorization artifact
6. Do not run production shadow or canary or change production routing
7. Do not restart rp-friend or the default gateway merely to qualify PAG-1
8. Do not mutate RetroPick / Android source
9. Do not push Engineering OS or upstream Hermes
