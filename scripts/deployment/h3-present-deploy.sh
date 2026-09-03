#!/usr/bin/env bash
# Print the H3 hash-locked install command. Does not apply the live patch.
set -euo pipefail
# shellcheck source=../lib/repo-root.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/../lib/repo-root.sh"
ROOT="$(_eos_repo_root_from "${BASH_SOURCE[0]}")"
PATCH="$ROOT/patches/hermes/live/0001-worker-spawn-transform-live.patch"
HASH="$(sha256sum "$PATCH" | awk '{print $1}')"
echo "HUMAN ACTION REQUIRED — H3"
echo
echo "artifact_sha256=$HASH"
echo "base_runtime_hash=c0106e50e7ecedb3ce34e785d949725dc4e0e457"
echo "expected_sha256=51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4"
if [[ "$HASH" != "51d4dd4d003143cdfea07d53668e8079f6d5163dc0a2777b3d5c3efd0001ecd4" ]]; then
  echo "FAIL: live patch hash drifted" >&2
  exit 1
fi
echo
echo "Copy the example manifest, set a unique nonce (not *example* / *not-authorizing*),"
echo "then print canonical bytes to sign off-VPS (no private key on this VPS)."
echo "After H1, canonical/install MUST use the protected deploy-tool; the plugin"
echo "source is /usr/local/lib/hermes-eos/deploy/pag2/eos-actuation-plugin/."
echo
cat <<'EOF'
cp /opt/hermes-engineering-os/deploy/pag2/h3-live-patch.manifest.example.json /tmp/h3.manifest.json
# edit nonce in /tmp/h3.manifest.json
TOOL=/usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py
if [[ ! -x "$TOOL" ]]; then
  TOOL=/opt/hermes-engineering-os/scripts/deployment/hermes-eos-deploy-tool.py
fi
python3 "$TOOL" canonical \
  --manifest /tmp/h3.manifest.json \
  --artifact /opt/hermes-engineering-os/patches/hermes/live/0001-worker-spawn-transform-live.patch
# Sign the printed hex off-VPS. Then, as hermes-op:
sudo /usr/local/lib/hermes-eos/hermes-eos-deploy-tool.py install \
  --manifest /tmp/h3.manifest.json \
  --artifact /opt/hermes-engineering-os/patches/hermes/live/0001-worker-spawn-transform-live.patch \
  --signature HEX_DETACHED_SIGNATURE
# install reloads affected gateway units (USR1 in-band) and the actuator
# so the spawn-transform is live. Do not use git pull.
EOF
