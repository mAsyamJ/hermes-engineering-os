# Evaluation Runner

CLI: `scripts/evaluate.sh` → `python -m engineering_os.evaluation`

Flags: `--task` `--board` `--profile` `--dry-run` `--recompute` `--explain`
`--json` `--incremental` `--trees-candidate` `--trees-baseline`

Incremental sweep uses advisory lock `420260827`. Overlap returns `locked`.
Concurrency: 1. Systemd user timer `hermes-eos-evaluate.timer` every 5 minutes.

Does not use the Kanban dispatcher or Hermes Cron. Does not mutate Hermes.
