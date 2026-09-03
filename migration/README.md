# Filesystem migration control plane

Distinct from `migrations/` (SQL).

| Artifact | Role |
|---|---|
| `path-inventory.json` | Machine-readable path inventory |
| `path-dependency-graph.json` | Readers/writers + systemd/import edges |
| `filesystem-normalization.yaml` | Applied moves (`moves_executed: true`; statuses `done` / `deferred`) |
| `path-map.yaml` | old→new map for stale-path scans |
| `compatibility.yaml` | Transitional shims, permanent bins, deferred Hermes-root debt |
| `ARCHITECTURE_FREEZE.json` | Freeze gate marker |
| `_build_phase1_inventory.py` | Regenerator used for Phase 1 |

## Final freeze status

- `moves_executed: true` after apply on branch `filesystem-normalization`.
- Deferred (intentional): Hermes-root `dashboard.log`, `gateway-starts.log`, and `~/.hermes/scripts` (writer/policy).
- Compatibility shims remain **transitional** with explicit `remove_when` conditions — see `compatibility.yaml`.
- Stable `bin/*` wrappers are **permanent** public entrypoints.

## Compatibility debt

See `compatibility.yaml` for reason, risk, priority, and removal conditions per artifact. No vague "cleanup later."
