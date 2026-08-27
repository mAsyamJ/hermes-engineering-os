# Observability compose

Loopback Phoenix + dedicated PostgreSQL for Engineering OS.

Images are pinned by tag and digest. PostgreSQL has no host port. Phoenix binds `127.0.0.1:6006` only. There is no OpenTelemetry Collector.

```bash
cd /opt/hermes-engineering-os
install -m 0600 deploy/observability/.env.example deploy/observability/.env
# fill secrets, then:
./scripts/start-observability.sh
./scripts/verify-observability.sh
```

Do not attach this stack to RetroPick networks or volumes.
