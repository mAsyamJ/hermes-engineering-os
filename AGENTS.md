# Engineering OS Agent Rules

- Hermes Agent is the runtime. Do not add a second orchestrator, worker owner,
  scheduler, retry engine, or task database.
- Agent OS (`agent-os-router`) is a capability index/router only — not a
  Kanban owner, worker owner, or second skill database. Disable via
  `scripts/agent-os/rollback-agent-os.sh` without wiping Hermes state.
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
- Analytics must fail open. `hermes_engineering` is derived. Do not use the
  Kanban dispatcher or Hermes Cron for refresh. Do not publish Postgres.
- Evaluation must fail open. Do not execute candidate code in production
  worktrees. Do not mount Docker socket into candidate containers. Do not run
  a live LLM judge.
- Performance must fail open. Do not rank models, route traffic, or treat
  observational comparisons as causal. Do not restart `rp-friend`.
- Experiments must fail open. Do not auto-route production, spend LLM budget,
  or treat fixture A/A / known-effect results as production causal proof.
- Adaptation must fail open to Hermes and fail closed for candidate policy.
  Do not auto-promote. Do not treat TEST approval as production authorization.
  Do not patch live Hermes core or mutate Kanban to apply policy.
- PAR must not fake a human approval boundary, deploy the isolated Hermes
  patch live, run paid LLM experiments without an authorization artifact,
  change sudoers/SSH, or run production canary.
- PAG-1 must not execute operator bootstrap, self-authorize LLM budget, push
  Engineering OS or upstream Hermes, or deploy the spawn transform to live
  Hermes. `scripts/verification/verify-operator-boundary.sh` is read-only.
- PAG-2 must not fake H1 PASS, create principals, cut over the live gateway,
  self-authorize LLM budget, deploy spawn-transform, or push. Human gates
  are H1 → H2 → experiment → H3. `scripts/verification/verify-operator-boundary.sh` is
  read-only and currently `READY_FOR_HUMAN`.
- After H1 PASS, present H2 with `scripts/deployment/h2-present-budget.sh`. After the
  exact authorize phrase, `python -m engineering_os.experiments run-real`
  then `analyze-real`. H3 is hash-locked deploy-tool plus
  `deploy/pag2/eos-actuation-plugin/` (not the ubuntu `/opt` symlink).
  Fail-closed probes: `scripts/deployment/pag2-as-runtime.sh pag2-probe` after H1
  (no confirmatory candidate). Evidence-gated: `scripts/deployment/pag2-shadow.sh`,
  `scripts/deployment/pag2-canary.sh`, `scripts/deployment/pag2-rollback.sh`. Canary bind:
  `scripts/deployment/pag2-bind-canary.sh` (hermes-op). Machine dashboard:
  `scripts/deployment/pag2-status.sh`.
- H1 copy-paste: `.runtime/operator-bootstrap/H1_COMMANDS.md`. Mechanical
  cutover `scripts/deployment/h1-cutover.sh` refuses ubuntu. Do not apply the live
  spawn-transform until H3.
- GitHub is read-first. Do not create branches, commits, PRs, checks, comments,
  or Kanban mutations from this plugin.
- Keep upstream pins, licenses, and every vendored file's provenance current.
- Use `scripts/deployment/uninstall-plugin.sh`; never use the built-in remove command for
  the external symlink.
- Run `bin/hermes-eos-verify` before declaring changes complete.

