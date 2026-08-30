#!/usr/bin/env bash
# Production IPC probe as hermes-runtime. hermes-op only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "$(id -u)" -ne 0 || "${SUDO_USER:-}" != "hermes-op" ]]; then
  echo "REFUSED: run via sudo from hermes-op" >&2
  exit 1
fi
cmd="${1:-pag2-shadow}"
shift || true
exec runuser -u hermes-runtime -- env \
  PYTHONPATH=/usr/local/lib/hermes-eos:/usr/lib/hermes-runtime/hermes-agent \
  HERMES_EOS_ACTUATOR_SOCK=/run/hermes-eos/actuator.sock \
  HERMES_EOS_REPO=/opt/hermes-engineering-os \
  EOS_EXPERIMENT_RUNTIME=/opt/hermes-engineering-os/.runtime/experiments \
  /usr/lib/hermes-runtime/venv/bin/python -m engineering_os.adaptation "$cmd" "$@"
