# Engineering OS Repository Layout (Target)

**Status:** Phase 1 architecture freeze — target shape adapted to **live** modules
**Repository:** `/opt/hermes-engineering-os`
**Rule:** Do not create empty architectural theater. Every directory must earn its place.

This document freezes the *intended* layout used by `migration/filesystem-normalization.yaml`. Apply only after the manifest gate; Phase 0–1 does not move files.

---

## Target tree (adapted)

```
/opt/hermes-engineering-os/
├── README.md
├── AGENTS.md
├── ARCHITECTURE.md
├── SECURITY.md
├── DECISIONS.md
├── OPERATIONS.md
├── RUNBOOK.md
├── TESTING.md
├── UPGRADE.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── uv.lock
├── plugin.yaml                 # Hermes engineering-os (ROOT REQUIRED)
├── __init__.py                 # engineering-os register()
│
├── agent_os/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── classifier.py       # from classify.py
│   │   ├── router.py
│   │   └── resolver.py
│   ├── registry/
│   │   ├── schema.py           # from agent_os/schema.py
│   │   ├── inventory.py
│   │   ├── generate.py
│   │   ├── ingest/
│   │   │   └── github.py       # from ingest_github.py
│   │   ├── sources_util.py
│   │   └── data/               # registry JSON/YAML (existing files stay)
│   ├── lifecycle/
│   │   └── sync.py             # from lifecycle.py
│   ├── integrations/
│   │   └── hermes/
│   │       └── plugin/         # from agent_os/plugin/
│   ├── policies/
│   ├── bundles/
│   ├── knowledge/
│   └── # transitional re-export shims at old module paths
│
├── engineering_os/             # KEEP — already packaged by domain
├── integrations/
├── dashboard/
├── deploy/
├── experiments/
├── config/
├── migrations/                 # SQL only
├── migration/                  # filesystem IA manifests/inventory
├── policies/
├── patches/
├── provenance/
├── requirements/
├── vendor/
├── upstream/
├── evidence/                   # historical phase evidence
│
├── bin/                        # stable operator commands (apply phase)
│   ├── hermes-eos-verify
│   ├── agent-os-verify
│   ├── agent-os-regenerate
│   ├── agent-os-status
│   ├── eos-analytics-materialize
│   ├── eos-evaluate
│   ├── eos-experiments-materialize
│   ├── eos-performance-materialize
│   ├── eos-adaptation-materialize
│   └── eos-layout-migrate
│
├── scripts/
│   ├── agent-os/
│   ├── adaptation/
│   ├── analytics/
│   ├── observability/
│   ├── evaluation/
│   ├── experiments/
│   ├── database/
│   ├── deployment/
│   ├── security/
│   ├── maintenance/
│   ├── migration/
│   ├── verification/
│   └── lib/                    # shared helpers only when justified
│
├── tests/
│   ├── python/                 # KEEP discovery path
│   ├── agent_os|adaptation|analytics|evaluation|experiments|performance/
│   ├── node/
│   ├── fixtures/
│   └── evidence/
│       └── layout-migration/
│
└── docs/
    ├── README.md               # documentation map (apply phase)
    ├── architecture/
    │   ├── filesystem/
    │   │   ├── root-contract.md
    │   │   ├── repository-layout.md
    │   │   ├── hermes-home-map.md
    │   │   └── HERMES_HOME_AUTHORITY_MAP.md  # after git mv
    │   ├── system/
    │   └── decisions/
    ├── agent-os/
    │   ├── routing/
    │   ├── skills/
    │   ├── profiles/
    │   ├── security/
    │   └── operations/
    ├── adaptation/
    ├── analytics/
    ├── evaluation/
    ├── experiments/
    ├── observability/
    ├── operations/
    │   ├── runbooks/
    │   ├── deployment/
    │   ├── recovery/
    │   ├── upgrades/
    │   └── migrations/
    ├── security/
    ├── reference/
    └── reports/
        ├── phases/
        ├── pag/
        ├── production/
        ├── acceptance/
        ├── agent-os/
        ├── migration/
        └── historical/
```

---

## Agent OS package decomposition (minimal)

| Current | Target | Compatibility |
|---|---|---|
| `agent_os/classify.py` | `agent_os/core/classifier.py` | Re-export `agent_os.classify` |
| `agent_os/router.py` | `agent_os/core/router.py` | Re-export `agent_os.router` |
| `agent_os/resolver.py` | `agent_os/core/resolver.py` | Re-export `agent_os.resolver` |
| `agent_os/schema.py` | `agent_os/registry/schema.py` | Re-export |
| `agent_os/inventory.py` | `agent_os/registry/inventory.py` | Re-export |
| `agent_os/generate.py` | `agent_os/registry/generate.py` | Re-export |
| `agent_os/ingest_github.py` | `agent_os/registry/ingest/github.py` | Re-export |
| `agent_os/lifecycle.py` | `agent_os/lifecycle/sync.py` | Re-export `agent_os.lifecycle` |
| `agent_os/plugin/` | `agent_os/integrations/hermes/plugin/` | Update symlink `~/.hermes/plugins/agent-os-router` + re-export package path if needed |

Keep: `registry/` data files, `policies/`, `bundles/`, `knowledge/`.

Do not rename for style alone. Update `pyproject`/tests/scripts/docs in the same apply wave.

---

## Docs normalization principles

- Prefix clusters (`ADAPTATION_*`, `ANALYTICS_*`, …) map to domain directories.
- Phase/PAG/production/Agent OS reports → `docs/reports/...`.
- Durable runbooks ≠ historical evidence.
- Each major category gets a short `README.md` index (apply phase).
- Root `README.md` links to `docs/reports/agent-os/README.md`; links use **new** canonical paths.
- Use `git mv`; detect broken Markdown links automatically after moves.

---

## Scripts + bin principles

- Categorize by **actual purpose**, not only filename prefix (see inventory `proposed_destination`).
- Shared helpers → `scripts/lib/` only when shared by ≥2 domains.
- `bin/` wrappers: realpath-based repo root resolver; only high-value commands (systemd, CI, humans, hooks).
- Systemd `ExecStart` must switch to `bin/*` in the same apply wave as script moves (Class C).

---

## Tests

Preserve `tests/python` + `pyproject.toml` `testpaths`. Do not break `unittest discover` used by `scripts/verification/verify.sh`. Evidence remains under `tests/evidence/`.

---

## What we deliberately do NOT add at repo root

Empty `analytics/`, `evaluation/`, `adaptation/` top-level dirs (logic lives in `engineering_os/`).
A second Engineering OS tree.
`misc/`, `old/`, `tmp2/`, `final/`.

---

## Related artifacts

- [root-contract.md](root-contract.md)
- [hermes-home-map.md](hermes-home-map.md)
- `migration/path-inventory.json`
- `migration/path-dependency-graph.json`
- `migration/filesystem-normalization.yaml`
