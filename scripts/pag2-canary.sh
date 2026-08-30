#!/usr/bin/env bash
# Fail-closed PAG-2 one-task canary. ubuntu cannot impersonate hermes-runtime.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$ROOT"
exec python3 -m engineering_os.adaptation pag2-canary "$@"
