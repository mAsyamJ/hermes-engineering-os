# Phase 4 Prerequisites

Phase 4 (objective + structured evaluation engine) must not start until Phase 3 is COMPLETE in `PHASE3_REPORT.md`.

Required Phase 3 properties:

1. Versioned derived schema in `hermes_engineering`
2. Read-only source adapters
3. Phoenix queried via GraphQL, not internal SQL
4. Deterministic, idempotent, recomputable materializer
5. Historical in-scope backfill with fixture exclusion
6. UNKNOWN preserved; Kanban DONE ≠ verified success
7. Analytics API read-only; fail-open to Hermes
8. Backup restore and source recompute both proven

Phase 4 must not change Hermes canonical task state automatically.
Do not implement Phase 4 from this document.
