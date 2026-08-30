# Runbook

## Verify

```bash
cd /opt/hermes-engineering-os
./scripts/verify.sh
```

## Install

The repository must be clean and all plugin checks must pass.

```bash
./scripts/install-plugin.sh
systemctl --user restart hermes-dashboard.service
./scripts/dashboard-request.py /api/plugins/engineering-os/health
```

Never restart either Hermes gateway.

## Rescan frontend manifests

```bash
./scripts/rescan-dashboard.sh
```

Rescan does not mount a new Python router. A first installation or backend file
change requires all-plugin preflight and a dashboard-only restart.

## Roll back

```bash
./scripts/uninstall-plugin.sh
systemctl --user restart hermes-dashboard.service
```

The uninstall script disables first, confirms the backend runtime gate is 404,
rescans, and unlinks only when the symlink resolves to this repository. Do not
run `hermes plugins remove engineering-os`.

## Observability stack

```bash
./scripts/start-observability.sh
./scripts/verify-observability.sh
./scripts/observability-db-backup.sh
./scripts/observability-db-verify.sh /var/backups/hermes-engineering-os/observability-<stamp>
./scripts/stop-observability.sh
```

Phoenix: `http://127.0.0.1:6006`. Never attach this compose project to RetroPick
networks or volumes. Restarting Phoenix or observability Postgres is allowed;
never restart either Hermes gateway for OTel.

## Analytics

```bash
./scripts/analytics-migrate.sh
./scripts/analytics-db-roles.sh
./scripts/analytics-materialize.sh --json
./scripts/analytics-explain.sh <task_id> [board]
./scripts/verify-analytics-data.sh
systemctl --user enable --now hermes-eos-analytics.timer
systemctl --user disable --now hermes-eos-analytics.timer
```

Analytics API: `http://127.0.0.1:9120` (loopback). Dashboard proxy:
`/api/plugins/engineering-os/analytics*`, `/evaluations*`, `/performance*`,
and `/experiments*`.
Manual refresh is the materialize script; disable the timer rather than the
Kanban dispatcher.

## Evaluation

```bash
./scripts/analytics-migrate.sh
./scripts/evaluate.sh --incremental --json
./scripts/evaluate.sh --explain --task t_eval_canary_a --board eos-phase4-eval
./scripts/evaluation-canary.sh
./scripts/verify-evaluation-data.sh
systemctl --user enable --now hermes-eos-evaluate.timer
```

Evaluation API: `http://127.0.0.1:9120/evaluations*`. Never restart rp-friend
for evaluation work.

## Performance

```bash
./scripts/analytics-migrate.sh
./scripts/performance-materialize.sh --dry-run --json
./scripts/performance-materialize.sh --json
./scripts/verify-performance-data.sh
systemctl --user enable --now hermes-eos-performance.timer
```

Performance API: `http://127.0.0.1:9120/performance*`. Observational only.
Never restart rp-friend.

## Experiments

```bash
./scripts/analytics-migrate.sh
./scripts/experiment.sh validate fixture-aa-v1
./scripts/experiment.sh preregister fixture-aa-v1
./scripts/experiment.sh assign fixture-aa-v1
./scripts/experiment.sh run-fixture fixture-aa-v1
./scripts/experiment.sh analyze fixture-aa-v1 --final
./scripts/verify-experiment-data.sh
systemctl --user enable --now hermes-eos-experiments.timer
```

Experiments API: `http://127.0.0.1:9120/experiments*`. GET-only. No auto-route.
Never restart rp-friend.

## Adaptation

```bash
./scripts/control-db-init.sh
./scripts/control-db-roles.sh
./scripts/adapt.sh recommend fixture-known-effect-v1
./scripts/adapt.sh compile-policy <recommendation_id> --policy fixture-known-effect-policy-v1
./scripts/adapt.sh approve-test fixture-known-effect-policy-v1 --stage A
./scripts/adapt.sh shadow-start fixture-known-effect-policy-v1 --board retropick-markets-release
./scripts/adapt.sh canary-start-fixture fixture-known-effect-policy-v1
./scripts/adapt.sh disable-all --reason emergency
./scripts/verify-adaptation-data.sh
systemctl --user enable --now hermes-eos-adaptation.timer
```

`adapt approve` (production) returns `BLOCKED_APPROVAL_BOUNDARY`.
Adaptation API: `http://127.0.0.1:9120/adaptation*`. GET-only. No auto-promote.
Never restart rp-friend. Never mutate Kanban to apply policy.

## Production Adaptation Readiness

```bash
./scripts/control-db-migrate.sh
curl -fsS http://127.0.0.1:9120/adaptation/readiness
curl -fsS http://127.0.0.1:9120/adaptation/readiness/authority
```

Do not apply `patches/hermes/0001-pre-worker-spawn-hook.patch` or
`patches/hermes/upstream/0001-worker-spawn-transform.patch` to live Hermes.
Do not create `.runtime/experiments/LLM_BUDGET_AUTHORIZATION` without a human
budget grant. Do not generate a production signing private key on this VPS.
See `docs/PRODUCTION_OPERATOR_HANDOFF.md` and `.runtime/operator-bootstrap/`.
Read-only boundary check: `./scripts/verify-operator-boundary.sh`.
PAG-2 hardening check: `./scripts/verify-pag2-hardening.sh`.
H1 baseline capture (read-only): `./scripts/capture-h1-baseline.sh`.
PAG-2 gate dashboard (read-only): `./scripts/pag2-status.sh`.
System unit templates for hermes-op live in `deploy/pag2/` and must not be
installed by ubuntu.
H1 copy-paste: `.runtime/operator-bootstrap/H1_COMMANDS.md`.
Mechanical H1 cutover (hermes-op only): `./scripts/h1-cutover.sh`.
Read-only H1 preflight: `./scripts/h1-preflight.sh`.
Post-H1 IPC probes as hermes-runtime (hermes-op only): `./scripts/pag2-as-runtime.sh pag2-probe`.
Evidence-gated shadow remains `pag2-shadow` after `QUALIFIED_CANDIDATE`.
H2 present: `./scripts/h2-present-budget.sh`. Persist only after H1 PASS and
the exact phrase: `./scripts/h2-write-authorization.sh`.
H3 present (does not apply): `./scripts/h3-present-deploy.sh`.
Canary sequence (hermes-op): `.runtime/operator-bootstrap/CANARY_COMMANDS.md`
and `./scripts/pag2-bind-canary.sh`. Persist auto-disable:
`./scripts/pag2-rollback-persist.sh` (hermes-op; ubuntu/runtime cannot write
actuator state).
Secret-free backup: `./scripts/pag2-backup.sh`. Isolated restore rehearsal:
`./scripts/pag2-restore-rehearsal.sh`.
Fail-closed production probes: `./scripts/pag2-shadow.sh`,
`./scripts/pag2-canary.sh`, `./scripts/pag2-rollback.sh`. ubuntu IPC is
`BLOCKED_PEER`; use `pag2-as-runtime.sh` after H1.

## Evidence states

- `AVAILABLE`: authoritative read completed.
- `DEGRADED`: source failed or timed out; Hermes continues.
- `UNKNOWN`: explicit correlation evidence is absent.
- `BLOCKED_AUTH`: GitHub API credentials are unavailable or rejected.

