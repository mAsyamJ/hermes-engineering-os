# Phase 2 Entry Check

Captured: 2026-08-27T15:43:19Z  
Snapshot: `tests/evidence/phase2-entry-20260827T154319Z.json`  
Gate 2.0: **PASS**

## Phase 1 freeze

| Check | Evidence | Result |
|---|---|---|
| Engineering OS HEAD | `7df2026fc97fbe2a9b5ff65c8c68abadbe60b50f` | PASS |
| Author / subject | `mAsyamJ <jayanegara.asyam@gmail.com>` `docs: publish Phase 1 implementation report` | PASS |
| Working tree | clean except this Phase 2 evidence/docs work | PASS at freeze (pre-mutation) |
| Plugin symlink | `~/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os` | PASS |
| Plugin health | `/api/plugins/engineering-os/health` HTTP 200, `AVAILABLE`, `read-only` | PASS |
| Dashboard | `127.0.0.1:9119` HTTP 200, PID `4021289` | PASS |
| Observability | `DEGRADED`, `sdk_available=false`, `phoenix=NOT_DEPLOYED`, `fail_open=true` | PASS expected |
| Enabled plugins | `engineering-os`, `hermes_otel`, `superpowers` | PASS |
| Phase 1 matrix | `docs/PLUGIN_VERIFICATION_MATRIX.md` — no UNKNOWN | PASS |
| Upstream lock | `briancaffey/hermes-otel` `c76bea8434e6cc8b51c835bb57c514a5eb71e857` | PASS |
| Phase 0 backup | `/var/backups/hermes-engineering-os/20260827T120255Z` SHA256SUMS | PASS |

## Hermes runtime

| Check | Evidence | Result |
|---|---|---|
| Version | Hermes Agent v0.20.0 (2026.8.3) | PASS |
| Python | 3.11.15 `/home/ubuntu/.hermes/hermes-agent/venv/bin/python` | PASS |
| Source HEAD | `c0106e50e7ecedb3ce34e785d949725dc4e0e457` | PASS |
| Source status | `main...origin/main [ahead 1, behind 1]`; `M package-lock.json` | PASS recorded; do not repair |
| Default gateway | PID `2381797` active | PASS unchanged vs Phase 1 |
| rp-friend | PID `924` `hermes_cli.main --profile rp-friend gateway run` | PASS unchanged |
| hermes_otel install | `~/.hermes/plugins/hermes_otel` present, OpenTelemetry packages absent | PASS deferred |
| Kanban board | `retropick-markets-release` 101 tasks / 122 runs / 0 running | PASS healthy |
| Dispatcher lock | board-scoped `kanban.db.dispatch.lock`; owner rp-friend | PASS |

## Production boundaries (Phase 2 baseline)

HEAD identity matches Phase 1 post-install. Porcelain hashes in this snapshot:

- `/opt/retropick` HEAD `a8edf7dd3e7195aea6f1c826fcf2199ead525162` porcelain_sha256 `99693428619084fcfe93c876dc4517e2ced759ae5ab6cda1cb7b6625618247e5` count 8
- `/opt/retropick-android` HEAD `e962490dab3ac1072d9ee6371eb1077c0a05c0ac` porcelain_sha256 `7addaea2004cfeeab26da0c76be8bcf71e94522d49c04f8d9dca2a0bddbbf4e9` count 39

These match `tests/evidence/post-install-20260827T151109Z.json`. Pre-existing dirty trees (`graphify-out*`, Android `out/`) are **not** cleaned. Phase 2 regressions compare against this snapshot.

Docker (9 containers): RetroPick rehearsal/dev only. Pre-existing unhealthy: `retropick-markets-rehearsal-markets-api-1`. Postgres published at `127.0.0.1:5433` and `127.0.0.1:5434`. No Phoenix, no dedicated Engineering OS Postgres.

## Storage / listeners

- Root: 63.9% used, 25.85 GiB free (≥20 GiB required)
- RAM: 7.6 GiB total, ~4.8 GiB available; swap 2.0 GiB (578 MiB used)
- Listeners: `127.0.0.1:9119`, `127.0.0.1:5433`, `127.0.0.1:5434`. Ports 6006/4317/4318 unused.

## Non-blocking accepted states

- GitHub API: `BLOCKED_AUTH`
- hermes_otel: dependency-degraded / fail-open
- Cron: pre-existing degraded (Phase 1)
- Hermes source drift: preserved, not repaired

## Gate 2.0 decision

**PASS.** Hermes venv mutation and Phoenix deploy are allowed. No unexplained runtime PID/HEAD/container drift versus Phase 1.
