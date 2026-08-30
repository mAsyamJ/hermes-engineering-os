#!/usr/bin/env bash
# Fail-closed PAG-2 production shadow. Does not mutate Kanban.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
exec python3 -m engineering_os.adaptation pag2-shadow
