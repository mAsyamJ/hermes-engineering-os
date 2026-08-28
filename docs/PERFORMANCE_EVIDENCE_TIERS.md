# Performance Evidence Tiers

Config: `config/performance-evidence-tiers.yaml` version `phase5-tiers-v1`.

These are operational presentation rules, not statistical law. The config hash
is stored on materialization lineage. Classification uses **known_n**.

| Tier | known_n |
|---|---|
| NO_DATA | 0 |
| INSUFFICIENT | 1–9 |
| EXPLORATORY | 10–29 |
| PROVISIONAL | 30–99 |
| SUPPORTED | ≥100 |

p90 requires n≥20; p95 requires n≥40. OBSERVED_DIFFERENCE requires both sides
at least EXPLORATORY and non-overlapping Wilson intervals.
