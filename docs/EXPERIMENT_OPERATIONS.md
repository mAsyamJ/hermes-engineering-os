# Experiment Operations

CLI: `scripts/experiment.sh` → compose profile `experiments`
(`python -m engineering_os.experiments --json`).

Commands: validate, preregister, plan, assign, run-fixture, collect, analyze,
explain, invalidate `--reason`, status.

Timer: `hermes-eos-experiments.timer` runs
`scripts/experiment-materialize.sh` every 5 minutes. Disable with
`systemctl --user disable --now hermes-eos-experiments.timer`.

Dashboard GET `/experiments*` is read-only. Writes are CLI/config only.
Default LLM budget is 0. PRODUCTION scope is rejected by the loader.

Fail-open: experiment DB or sidecar outage degrades `/experiments*` without
failing Hermes `/health`. rp-friend is never restarted for this layer.
