#!/usr/bin/env bash
# Persist H2 budget only after H1 PASS and the exact human phrase.
# Never writes secrets. Never runs paid units.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
cd "$ROOT"
created_by="${1:-}"
expiry="${2:-}"
phrase="${3:-AUTHORIZE EXPERIMENT fa1b83d8583f832ac8ed15f456f12f9856aca1b26689d8859f1d6e5a7e3a870a WITH THE ABOVE HARD LIMITS}"
if [[ -z "$created_by" || -z "$expiry" ]]; then
  echo "usage: $0 <created_by> <rfc3339-expiry> [exact-phrase]" >&2
  echo "HUMAN ACTION REQUIRED — H2" >&2
  exit 2
fi
exec python3 -m engineering_os.experiments write-budget \
  --created-by "$created_by" \
  --expiry "$expiry" \
  --phrase "$phrase"
