#!/usr/bin/env bash
# Fail-closed PAG-2 one-task canary. ubuntu cannot impersonate hermes-runtime.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
cd "$ROOT"
exec python3 -m engineering_os.adaptation pag2-canary "$@"
