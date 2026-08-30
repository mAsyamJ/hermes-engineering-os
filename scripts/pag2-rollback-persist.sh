#!/usr/bin/env bash
# Persist future-only auto-disable to protected actuator state. hermes-op only.
# Does not kill a running worker. Does not auto-promote. Does not mutate git.
set -euo pipefail
if [[ "$(id -u)" -ne 0 || "${SUDO_USER:-}" != "hermes-op" ]]; then
  echo "REFUSED: run via sudo from hermes-op" >&2
  exit 1
fi
export PYTHONPATH=/usr/local/lib/hermes-eos:/usr/lib/hermes-runtime/hermes-agent
export HERMES_EOS_ACTUATOR_STATE=/var/lib/hermes-actuator/state.json
export HERMES_EOS_REPO=/opt/hermes-engineering-os
exec /usr/lib/hermes-runtime/venv/bin/python -m engineering_os.adaptation pag2-rollback \
  --reason "${1:-pag2 auto-disable}"
