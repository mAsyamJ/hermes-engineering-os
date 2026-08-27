# Phoenix Pin

| Field | Value |
|---|---|
| Selection method | Newest stable Docker Hub `version-*` tag that passed Stage 2.4 GraphQL ingest |
| Rejected | `latest`, `nightly`, commit tags |
| Image | `arizephoenix/phoenix:version-20.4.0` |
| Digest | `sha256:8af594ab0342cc32acc4167f472fb89b4e25f5eb8d5e26c353bf4e102fddb693` |
| Architecture | linux/amd64 |
| License | Elastic License 2.0 (self-host; not offered as a third-party managed service) |
| OTLP | HTTP `http://127.0.0.1:6006/v1/traces` |
| UI | `http://127.0.0.1:6006` |
| gRPC 4317 | not published |
| Query API | GraphQL `/graphql` via `node(id: projectId) { ... on Project { spans } }` (root `Query.spans` is gone in 20.x) |
| Metrics OTLP | `/v1/metrics` returned 405 on 20.4.0; traces still ingest. No Collector added. |

## PostgreSQL pin

| Field | Value |
|---|---|
| Image | `postgres:16.15` (Phoenix upstream compose uses major 16) |
| Pulled digest | `sha256:f1c3376c26f2609ab9f29f71f824103fe2fcd8ee0346485cb6122a4f93df6f94` |
| Host ports | none |
| Volume | `hermes-eos-observability-pgdata` (new) |
| Databases | `phoenix` (role `phoenix`), `hermes_engineering` (owner `hermes_engineering`; writer/reader roles for Phase 3 analytics) |
| Superuser | container bootstrap `eos_admin` only; app roles are LOGIN without SUPERUSER |

## Collector

Not deployed. Direct hermes-otel OTLP/HTTP to Phoenix is proven by Stage 2.4 (`GATE_2_4_PASS`, 4 spans, parent/child, real trace id).
