# Documentation map

Start here. Root `README.md` links to this file rather than enumerating every document.

## Domains

- [adaptation/](./adaptation/) — ** Policy, rollback, canary, and operational docs for the adaptation control plane.
- [agent-os/](./agent-os/) — ** Capability control plane, routing, skills, profiles, security, operations.
- [analytics/](./analytics/) — ** Analytics database, materialization, DQ, and operations.
- [architecture/](./architecture/) — ** System architecture, filesystem contracts, ADRs.
- [evaluation/](./evaluation/) — ** Evaluation runner, sandbox, evidence model, and security.
- [experiments/](./experiments/) — ** Experiment protocol, validity, assignment, and recovery.
- [observability/](./observability/) — ** OTel, performance materialization, and observability ops.
- [operations/](./operations/) — ** Runbooks, deployment, recovery, upgrades, Hermes home ops.
- [reference/](./reference/) — ** Cross-cutting reference docs that do not fit a single domain.
- [reports/](./reports/) — ** Historical phase/PAG/production/Agent OS evidence reports — not operational runbooks.
- [security/](./security/) — ** Security-focused documentation (domain-specific security also lives under adaptation/evaluation/experiments).

## Conventions

- Durable documentation lives under domain folders.
- Historical reports live under `reports/`.
- Filesystem contracts: [architecture/filesystem/](./architecture/filesystem/).
- Prefer canonical paths after filesystem normalization; do not resurrect flat `docs/*.md` roots.
