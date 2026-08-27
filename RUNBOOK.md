# Runbook

## Verify

```bash
cd /opt/hermes-engineering-os
./scripts/verify.sh
```

## Install

The repository must be clean and all plugin checks must pass.

```bash
./scripts/install-plugin.sh
systemctl --user restart hermes-dashboard.service
./scripts/dashboard-request.py /api/plugins/engineering-os/health
```

Never restart either Hermes gateway.

## Rescan frontend manifests

```bash
./scripts/rescan-dashboard.sh
```

Rescan does not mount a new Python router. A first installation or backend file
change requires all-plugin preflight and a dashboard-only restart.

## Roll back

```bash
./scripts/uninstall-plugin.sh
systemctl --user restart hermes-dashboard.service
```

The uninstall script disables first, confirms the backend runtime gate is 404,
rescans, and unlinks only when the symlink resolves to this repository. Do not
run `hermes plugins remove engineering-os`.

## Evidence states

- `AVAILABLE`: authoritative read completed.
- `DEGRADED`: source failed or timed out; Hermes continues.
- `UNKNOWN`: explicit correlation evidence is absent.
- `BLOCKED_AUTH`: GitHub API credentials are unavailable or rejected.

