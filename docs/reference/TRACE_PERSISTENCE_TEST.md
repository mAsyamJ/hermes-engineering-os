# Trace Persistence Test

Gate 2.8: **PASS**

| Step | Evidence |
|---|---|
| Synthetic session | `persist-20260827T160042Z` |
| Trace id | `ba6cc2d4d520b3a31008f282b95240ab` |
| Spans | `agent`, `llm.gpt-4`, `api.gpt-4` (count 3) |
| After Phoenix-only recreate | same trace id, same spans |
| After Postgres restart + Phoenix start | same trace id, same spans |
| Alembic version after restart | `4aad9107d196` (no corrupt re-init) |
| Volume | `hermes-eos-observability-pgdata` retained |

Artifacts: `evidence/phase2/persist-before.txt`, `persist-after-phoenix.txt`, `persist-after-db.txt`.
