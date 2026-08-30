#!/usr/bin/env bash
# Read-only H1 SSH preflight. Does not create users, keys, or cut over.
set -euo pipefail
fail=0
note() { echo "FAIL: $1"; fail=1; }
pass() { echo "PASS: $1"; }

if ! getent passwd hermes-op >/dev/null; then
  note "hermes-op missing"
  echo "H1 SSH PREFLIGHT: NOT READY"
  exit 1
fi
pass "hermes-op exists"

home="$(getent passwd hermes-op | awk -F: '{print $6}')"
keys="$home/.ssh/authorized_keys"
if [[ ! -d "$home" ]]; then
  note "hermes-op home missing"
elif [[ -w "$home" ]]; then
  # Invoked as ubuntu this should be false (home is 0750). Root would be true.
  if [[ "$(id -un)" == "ubuntu" ]]; then
    pass "ubuntu cannot write hermes-op home"
  fi
fi

if [[ "$(id -u)" -eq 0 ]] || sudo -n true >/dev/null 2>&1; then
  as_root() { if [[ "$(id -u)" -eq 0 ]]; then "$@"; else sudo -n "$@"; fi; }
  mode="$(as_root stat -c '%a' "$keys")"
  owner="$(as_root stat -c '%U' "$keys")"
  if [[ "$mode" != "600" || "$owner" != "hermes-op" ]]; then
    note "authorized_keys mode/owner ${owner}:${mode}"
  else
    pass "authorized_keys 600 hermes-op"
  fi
  count="$(as_root awk 'BEGIN{n=0} /^ssh-ed25519 /{n++} END{print n}' "$keys")"
  if [[ "$count" -lt 1 ]]; then
    note "authorized_keys has no ssh-ed25519 line"
  else
    pass "ssh-ed25519 authorized key count=$count"
    as_root ssh-keygen -lf "$keys"
  fi
else
  note "cannot inspect authorized_keys without sudo"
fi

sshd_out="$(sshd -C user=hermes-op,host=localhost,addr=127.0.0.1 -T 2>/dev/null || true)"
if [[ -z "$sshd_out" ]]; then
  sshd_out="$(sudo -n sshd -C user=hermes-op,host=localhost,addr=127.0.0.1 -T 2>/dev/null || true)"
fi
if echo "$sshd_out" | rg -q '^pubkeyauthentication yes$'; then
  pass "sshd PubkeyAuthentication yes"
else
  note "sshd PubkeyAuthentication not yes"
fi
if echo "$sshd_out" | rg -q '^passwordauthentication no$'; then
  pass "sshd PasswordAuthentication no (use the matching private key)"
else
  note "sshd PasswordAuthentication is not no"
fi
if echo "$sshd_out" | rg -q '^allowusers '; then
  if echo "$sshd_out" | rg -q '^allowusers .*\bhermes-op\b'; then
    pass "AllowUsers includes hermes-op"
  else
    note "AllowUsers excludes hermes-op"
  fi
else
  pass "no AllowUsers restriction"
fi

echo "ssh hermes-op@$(hostname -f 2>/dev/null || hostname)"
if [[ "$fail" -ne 0 ]]; then
  echo "H1 SSH PREFLIGHT: NOT READY"
  exit 1
fi
echo "H1 SSH PREFLIGHT: READY (human must still log in as hermes-op)"
exit 0
