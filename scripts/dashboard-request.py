#!/usr/bin/env python3
"""Call one loopback dashboard GET route without exposing its session token."""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:9119"


def session_token() -> str:
    request = urllib.request.Request(BASE + "/", headers={"Host": "127.0.0.1:9119"})
    with urllib.request.urlopen(request, timeout=5) as response:
        html = response.read().decode("utf-8", "replace")
    match = re.search(r'__HERMES_SESSION_TOKEN__="([^"]+)"', html)
    if not match:
        raise RuntimeError("dashboard did not provide a loopback session token")
    return match.group(1)


def get(path: str) -> tuple[int, object]:
    if not path.startswith("/") or "://" in path:
        raise ValueError("path must be a dashboard-relative absolute path")
    token = session_token()
    request = urllib.request.Request(
        BASE + path,
        headers={"X-Hermes-Session-Token": token, "Host": "127.0.0.1:9119"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8", "replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        status = exc.code
    try:
        payload: object = json.loads(body)
    except json.JSONDecodeError:
        payload = {"body": body[:500]}
    return status, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--expect-status", type=int, default=200)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    status, payload = get(args.path)
    if not args.quiet:
        print(json.dumps({"http_status": status, "data": payload}, indent=2))
    if status != args.expect_status:
        raise SystemExit(f"expected HTTP {args.expect_status}, got {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

