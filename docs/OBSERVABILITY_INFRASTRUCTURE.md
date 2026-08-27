# Observability Infrastructure

Dedicated Engineering OS stack under `deploy/observability/`. Isolated from RetroPick Docker networks and volumes.

```
hermes-otel  --OTLP/HTTP-->  Phoenix :6006 (loopback)
                               |
                               v
                     hermes-eos-postgres (no host port)
                          /              \
                     phoenix DB     hermes_engineering DB
```

## Network and bind

- Compose project `hermes-eos-observability`
- Network `hermes-eos-observability` (bridge)
- Phoenix published `127.0.0.1:6006:6006`
- Postgres `expose: 5432` only
- No Caddy, no Collector, no 4317 host mapping

## Secrets

`deploy/observability/.env` is `0600`, gitignored. `.env.example` has placeholders only.

## Fail-open

Phoenix or Postgres outage must not stop Hermes. Engineering OS reports observability `DEGRADED`.

## Operations

See `scripts/start-observability.sh`, `stop-observability.sh`, `restart-observability.sh`, `verify-observability.sh`, `observability-db-backup.sh`.
