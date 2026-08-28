# Evaluation Operations

Enable: `systemctl --user enable --now hermes-eos-evaluate.timer`

Disable: `systemctl --user disable --now hermes-eos-evaluate.timer`

Manual: `scripts/evaluate.sh --incremental --json`

Explain: `scripts/evaluate.sh --explain --task <id> --board <board>`

API: `http://127.0.0.1:9120/evaluations*` GET-only. Dashboard proxy
`/api/plugins/engineering-os/evaluations*`.

Evaluation failure degrades `/evaluations*` only. Hermes `/health` stays
AVAILABLE. Phase 3 analytics timer is independent.

Storage: keep root free ≥20 GiB. Artifact dir
`/var/lib/hermes-engineering-os/evaluation-artifacts` mode 0700. No destructive
GC in Phase 4.
