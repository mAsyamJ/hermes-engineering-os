#!/usr/bin/env bash
set -euo pipefail
# Candidate container must not see host secrets, docker.sock, or network.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
IMAGE="hermes-eos-analytics:phase3"
WORKDIR="$(mktemp -d /tmp/eos-sandbox-XXXX)"
trap 'rm -rf "$WORKDIR"' EXIT
echo 'print("ok")' >"$WORKDIR/probe.py"
# Network none
if sudo -n docker run --rm --network none --user 65534:65534 --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,size=16m \
  --cap-drop ALL --security-opt no-new-privileges \
  -v "$WORKDIR:/input:ro" "$IMAGE" \
  python3 -c "import socket; socket.create_connection(('1.1.1.1',53),2)" \
  >/tmp/eos-net.out 2>&1; then
  echo "FAIL: candidate reached network" >&2
  exit 1
fi
echo "PASS: network none"
# Docker socket absent
sudo -n docker run --rm --network none --user 65534:65534 --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  -v "$WORKDIR:/input:ro" "$IMAGE" \
  python3 -c "import os; assert not os.path.exists('/var/run/docker.sock'); assert not os.path.exists('/home/ubuntu/.ssh')"
echo "PASS: docker.sock and ssh absent"
# Fake host secret not in container env
if sudo -n docker run --rm --network none --user 65534:65534 --read-only \
  --cap-drop ALL -v "$WORKDIR:/input:ro" -e HOME=/tmp "$IMAGE" \
  python3 -c "import os; assert 'FAKE_PHASE4_SECRET_ABC123' not in os.environ.get('FAKE','' ); print(os.environ.keys())" \
  | rg -q 'FAKE_PHASE4_SECRET_ABC123'; then
  echo "FAIL: secret in candidate output" >&2
  exit 1
fi
echo "PASS: candidate env has no planted secret"
echo "PASS: sandbox isolation"
