# Engineering OS Agent Rules

- Hermes Agent is the runtime. Do not add a second orchestrator, worker owner,
  scheduler, retry engine, or task database.
- Hermes Kanban is the only lifecycle authority. This product is read-only.
- Never conflate `hermes.kanban.task_id` with `hermes.runtime.task_id`.
- Do not mutate `/opt/retropick`, `/opt/retropick-android`, production
  worktrees, Docker workloads, Hermes source, or the Hermes virtual environment.
- Never restart a Hermes gateway. `hermes-gateway-rp-friend.service` owns the
  singleton dispatcher lock.
- Dashboard changes require all-plugin preflight, authenticated rescan, and
  only then a dashboard-only restart.
- Observability must fail open. Traces are derived from Hermes; Kanban remains
  the only task authority. Do not restart `rp-friend` to enable OTel.
- GitHub is read-first. Do not create branches, commits, PRs, checks, comments,
  or Kanban mutations from this plugin.
- Keep upstream pins, licenses, and every vendored file's provenance current.
- Use `scripts/uninstall-plugin.sh`; never use the built-in remove command for
  the external symlink.
- Run `scripts/verify.sh` before declaring changes complete.

