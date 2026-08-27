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


def pull_request_evidence(slug: str, branch: str) -> Evidence[dict[str, Any]]:
    """PR/check/merge evidence. Unauthenticated sessions stay BLOCKED_AUTH."""
    cli = GhCliTransport()
    try:
        authenticated = cli.authenticated()
    except (OSError, subprocess.TimeoutExpired):
        authenticated = False
    if not authenticated:
        return Evidence(
            EvidenceStatus.BLOCKED_AUTH,
            "github:pr",
            {
                "evidence_state": "BLOCKED_AUTH",
                "slug": slug,
                "branch": branch,
                "pr_number": None,
                "ci_conclusion": None,
                "merged": None,
            },
            detail="GitHub CLI API authentication is not configured",
        )
    if not slug or not branch:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "github:pr",
            {
                "evidence_state": "UNKNOWN",
                "slug": slug,
                "branch": branch,
                "pr_number": None,
                "ci_conclusion": None,
                "merged": None,
            },
            detail="missing slug or branch",
        )
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                "-X",
                "GET",
                "search/issues",
                "-f",
                f"q=repo:{slug} type:pr head:{branch}",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            env={"HOME": str(Path.home()), "PATH": os.environ.get("PATH", "/usr/bin:/bin")},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "github:pr",
            {"evidence_state": "UNKNOWN", "slug": slug, "branch": branch},
            detail=type(exc).__name__,
        )
    if result.returncode != 0:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "github:pr",
            {"evidence_state": "UNKNOWN", "slug": slug, "branch": branch},
            detail="gh api search failed",
        )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return Evidence(
            EvidenceStatus.DEGRADED,
            "github:pr",
            {"evidence_state": "UNKNOWN", "slug": slug, "branch": branch},
            detail="invalid GitHub JSON",
        )
    items = payload.get("items") or []
    if not items:
        return Evidence(
            EvidenceStatus.UNKNOWN,
            "github:pr",
            {
                "evidence_state": "NOT_FOUND",
                "slug": slug,
                "branch": branch,
                "pr_number": None,
                "ci_conclusion": None,
                "merged": None,
            },
            detail="no pull request for branch",
        )
    first = items[0]
    number = first.get("number")
    state = first.get("state")
    return Evidence(
        EvidenceStatus.AVAILABLE,
        "github:pr",
        {
            "evidence_state": "AVAILABLE",
            "slug": slug,
            "branch": branch,
            "pr_number": number,
            "pr_state": state,
            "ci_conclusion": None,
            "merged": state == "closed" and bool(first.get("pull_request", {}).get("merged_at"))
            if isinstance(first.get("pull_request"), dict)
            else None,
        },
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

