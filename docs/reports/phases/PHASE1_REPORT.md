# Phase 1 Implementation Report

Status: **PASS**  
Completed: 2026-08-27  
Product repository: `/opt/hermes-engineering-os`

## Delivered

- Five upstream repositories are cloned, detached at audited commits, ignored
  by product Git, and locked with exact license hashes and retrieval sizes.
- Official Hermes dashboard examples are preserved as compatibility references.
- MIT event coalescing and status transition/replay logic are narrowly adapted.
- Agent Kanban remains design-only; no FSL source, CSS, assets, or layout was
  vendored.
- The combined `engineering-os` user plugin is installed and enabled through
  `/home/ubuntu/.hermes/plugins/engineering-os` → `/opt/hermes-engineering-os`.
- Authenticated GET-only routes expose live Hermes runtime, canonical Kanban,
  profiles, workers, plugins, configured Git repositories, workspaces, GitHub
  evidence, and observability status.
- The SDK dashboard provides Overview, Tasks, Runs, Agents, Plugins, GitHub,
  Workspaces, and Observability views using live data.
- Deterministic clone, fixture, provenance, preflight, install, rescan,
  uninstall, boundary snapshot, and verification scripts are operational.

## Live state

- Plugin health: `AVAILABLE`, version `1.0.0`, mode `read-only`.
- Dashboard: active on loopback port 9119; final qualification PID `4021289`.
- Default gateway PID: `2381797`, unchanged.
- `rp-friend` gateway/dispatcher PID: `924`, unchanged and uninterrupted.
- GitHub SSH: authenticated as `mAsyamJ`.
- GitHub API: `BLOCKED_AUTH`, accepted by the Phase 1 contract.
- Existing `hermes_otel`: `DEGRADED`, fail-open because OpenTelemetry packages
  are intentionally deferred.
- Phoenix: not deployed.
- New PostgreSQL: not deployed.
- Storage: 63.9% used, 25.9 GiB free; product/upstream/build/browser footprint
  remains below 1 GiB.

## Verification

`scripts/verification/verify.sh` passed:

- all Phase 0 backup checksums;
- 13/13 vendored files mapped to provenance records;
- five isolated plugin import/register cases plus official dashboard checks;
- 9 Python adapter/backend/security tests;
- TypeScript checking and deterministic IIFE build;
- 3 Node reducer/SDK/bundle tests;
- 2 isolated Chromium dashboard tests;
- 1 installed live Chromium test across all eight views;
- authenticated live API and asset checks;
- production Git, Docker, gateway, dispatcher, storage, and secret gates.

Rollback was exercised end to end: disable first, backend gate returned 404,
manifest rescan passed, exact symlink was unlinked, disappearance was verified,
then the plugin was reinstalled, enabled, rescanned, and mounted by a
dashboard-only restart.

## Boundary results

- `/opt/retropick` HEAD and porcelain hash are exactly unchanged.
- `/opt/retropick-android` HEAD and porcelain hash are exactly unchanged.
- Docker names, images, states, health, and published ports are unchanged.
- Hermes source/virtual environment and systemd unit files are unchanged.
- No gateway restart, Kanban write, production Git write, Docker mutation, new
  listener, daemon, task database, scheduler, worker manager, Phoenix service,
  or PostgreSQL service occurred.

## Correlation contract

`hermes.kanban.task_id` is canonical. It remains distinct from
`hermes.runtime.task_id`, Kanban run ID, session, turn, API request, tool call,
Git SHA, GitHub PR/check, and OTel trace/span IDs. Missing explicit evidence is
reported as `UNKNOWN`; no heuristic relationship is asserted.

## Local commits

- `5410b04` initialize product and pinned upstream evidence
- `9437c41` license and vendor adoption decisions
- `4de1a11` isolated plugin qualification
- `112baee` read-only Hermes/Git/GitHub adapters
- `5822231` dashboard backend and UI
- `aade5ca` guarded deployment tooling
- `8a234d6` generated-bytecode provenance correction
- `e40a7da` live rollback and boundary qualification
- final documentation and refreshed evidence commit

No commit was pushed.

## Phase 2 readiness

Phase 2 may repair the existing `hermes_otel` installation only after another
environment snapshot and pinned-upstream comparison. Observability must remain
fail-open. If analytics storage is introduced later, use one dedicated Hermes
Engineering PostgreSQL server/container with isolated databases and roles;
never reuse RetroPick PostgreSQL.

Phase 1 stops here.

