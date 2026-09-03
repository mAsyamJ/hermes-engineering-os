#!/usr/bin/env bash
# Future-only auto-disable. Does not kill a running worker. Does not auto-promote.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
cd "$ROOT"
exec python3 -m engineering_os.adaptation pag2-rollback --reason "${1:-pag2 auto-disable}"
