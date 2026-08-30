# Experiment Operations

CLI: `scripts/experiment.sh` → compose profile `experiments`
(`python -m engineering_os.experiments --json`).

Commands: validate, preregister, plan, assign, run-fixture, collect, analyze,
explain, invalidate `--reason`, status, budget-limits, run-real.

`run-real` executes the confirmatory protocol only after H1 `status=PASS`
and `.runtime/experiments/LLM_BUDGET_AUTHORIZATION` exists. Persist that
artifact with `scripts/h2-write-authorization.sh` after the exact H2
phrase. Without it the command returns `READY_FOR_BUDGET_AUTHORIZATION`
or `BLOCKED_SECURITY_BOUNDARY` and executes zero units.
Each executed unit is evaluated with the `real-v1` Phase 4 profile
(`phase4.quality_vector.tests`). `analyze-real` persists `analysis.json`
with `QUALIFIED_CANDIDATE` or `VALID_NO_PROMOTION` and never auto-promotes.

Timer: `hermes-eos-experiments.timer` runs
`scripts/experiment-materialize.sh` every 5 minutes. Disable with
`systemctl --user disable --now hermes-eos-experiments.timer`.

Dashboard GET `/experiments*` is read-only. Writes are CLI/config only.
Default LLM budget is 0. PRODUCTION scope is rejected by the loader.

Fail-open: experiment DB or sidecar outage degrades `/experiments*` without
failing Hermes `/health`. rp-friend is never restarted for this layer.
