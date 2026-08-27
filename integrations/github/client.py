"""Bounded GitHub transports that never expose credentials."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from engineering_os.models import Evidence, EvidenceStatus


class Transport(Protocol):
    def repository(self, slug: str) -> dict[str, Any]: ...


class FixtureTransport:
    def __init__(self, fixtures: dict[str, dict[str, Any]]) -> None:
        self.fixtures = fixtures

    def repository(self, slug: str) -> dict[str, Any]:
        return dict(self.fixtures[slug])


class GhCliTransport:
    def authenticated(self) -> bool:
        result = subprocess.run(
            ["gh", "auth", "status", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            timeout=5,
            env={"HOME": str(Path.home()), "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        return result.returncode == 0

    def repository(self, slug: str) -> dict[str, Any]:
        result = subprocess.run(
            ["gh", "api", f"repos/{slug}"],
            check=True,
            capture_output=True,
            text=True,
            timeout=8,
            env={"HOME": str(Path.home()), "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
        return json.loads(result.stdout)


class PublicRestTransport:
    def repository(self, slug: str) -> dict[str, Any]:
        request = Request(
            f"https://api.github.com/repos/{slug}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "hermes-engineering-os"},
        )
        with urlopen(request, timeout=5) as response:
            return json.load(response)


def github_status(slugs: list[str] | None = None) -> Evidence[dict[str, Any]]:
    slugs = slugs or []
    cli = GhCliTransport()
    try:
        authenticated = cli.authenticated()
    except (OSError, subprocess.TimeoutExpired):
        authenticated = False
    if not authenticated:
        return Evidence(
            EvidenceStatus.BLOCKED_AUTH,
            "github:gh",
            {"authenticated": False, "repositories": slugs},
            detail="GitHub CLI API authentication is not configured",
        )
    repositories = {}
    try:
        for slug in slugs:
            repositories[slug] = cli.repository(slug)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "github:gh",
            {"authenticated": True, "repositories": repositories},
            detail=type(exc).__name__,
        )
    return Evidence(
        EvidenceStatus.AVAILABLE,
        "github:gh",
        {"authenticated": True, "repositories": repositories},
    )


def public_repository(slug: str, transport: Transport | None = None) -> Evidence[dict[str, Any]]:
    try:
        data = (transport or PublicRestTransport()).repository(slug)
        return Evidence(EvidenceStatus.AVAILABLE, "github:public-rest", data)
    except HTTPError as exc:
        status = EvidenceStatus.BLOCKED_AUTH if exc.code in (401, 403) else EvidenceStatus.DEGRADED
        return Evidence(status, "github:public-rest", {}, detail=f"HTTP {exc.code}")
    except (URLError, TimeoutError, OSError, KeyError) as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "github:public-rest",
            {},
            detail=type(exc).__name__,
        )

