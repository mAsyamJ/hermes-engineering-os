"""Merge GitHub tree evidence into per-skill curated registry rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_os import REGISTRY_DIR
from agent_os.registry.sources_util import allowlisted_repos, source_tier_for_repo

EVIDENCE = Path("/opt/hermes-engineering-os/tests/evidence/agent-os-github-skill-trees.json")


def load_github_expanded() -> list[dict[str, Any]]:
    if not EVIDENCE.exists():
        return []
    data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    allow = allowlisted_repos()
    rows: list[dict[str, Any]] = []
    for repo in data.get("repos") or []:
        repository = repo.get("repository") or ""
        branch = repo.get("default_branch") or "main"
        tier = source_tier_for_repo(repository)
        if repo.get("error") and not repo.get("skills"):
            rows.append(
                {
                    "skill_id": f"repo-error:{repository}",
                    "display_name": repository,
                    "description": f"Source inspect failed: {repo.get('error')}",
                    "repository": repository,
                    "install_state": "unreachable",
                    "trust_tier": tier,
                    "source_type": "github-tree",
                    "capabilities": [],
                    "domains": [],
                    "field_kinds": {"trust_tier": "CURATED", "install_state": "DERIVED"},
                }
            )
            continue
        for skill in repo.get("skills") or []:
            path = skill.get("path") or ""
            guess = skill.get("skill_id_guess") or "unknown"
            if guess in {"root", "skills", "."}:
                # Prefer repo leaf name for root SKILL.md
                guess = repository.split("/")[-1]
            skill_id = guess
            # Disambiguate collisions with repo prefix when needed later in generate
            identifier = f"{repository}/{path.removesuffix('/SKILL.md').removesuffix('SKILL.md')}".rstrip("/")
            if path == "SKILL.md":
                identifier = repository
            raw_url = f"https://raw.githubusercontent.com/{repository}/{branch}/{path}"
            hermes_id = f"{repository}/{path.removesuffix('/SKILL.md')}" if path != "SKILL.md" else repository
            rows.append(
                {
                    "skill_id": skill_id,
                    "display_name": skill_id,
                    "description": f"Curated skill from {repository} at {path}",
                    "native_path": "",
                    "source": repository,
                    "source_type": "github-tree",
                    "repository": repository,
                    "upstream_identifier": hermes_id,
                    "raw_url": raw_url,
                    "path": path,
                    "branch": branch,
                    "install_state": "not_installed",
                    "trust_tier": tier,
                    "security_state": "uninspected",
                    "allowlisted": repository in allow,
                    "capabilities": [],
                    "domains": [],
                    "triggers": [skill_id.replace("-", " ")],
                    "negative_triggers": [],
                    "when_to_use": [],
                    "when_not_to_use": [],
                    "field_kinds": {
                        "skill_id": "DERIVED",
                        "path": "DERIVED",
                        "trust_tier": "CURATED",
                        "install_state": "DERIVED",
                    },
                }
            )
    return rows


def write_expanded_cache() -> Path:
    rows = load_github_expanded()
    dest = REGISTRY_DIR / "github-expanded.json"
    dest.write_text(json.dumps({"version": 1, "skills": rows}, indent=2, sort_keys=True) + "\n")
    return dest
