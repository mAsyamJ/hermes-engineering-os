#!/usr/bin/env bash
# Persist a maximum_exposure=1 CANARY binding. hermes-op only. Does not actuate.
set -euo pipefail
if [[ "$(id -u)" -ne 0 || "${SUDO_USER:-}" != "hermes-op" ]]; then
  echo "REFUSED: run via sudo from hermes-op" >&2
  exit 1
fi
export PYTHONPATH=/usr/local/lib/hermes-eos:/usr/lib/hermes-runtime/hermes-agent
export HERMES_EOS_ACTUATOR_SOCK=/run/hermes-eos/actuator.sock
export HERMES_EOS_ACTUATOR_STATE=/var/lib/hermes-actuator/state.json
export HERMES_EOS_REPO=/opt/hermes-engineering-os
export EOS_EXPERIMENT_RUNTIME=/opt/hermes-engineering-os/.runtime/experiments
exec /usr/lib/hermes-runtime/venv/bin/python -m engineering_os.adaptation pag2-bind
