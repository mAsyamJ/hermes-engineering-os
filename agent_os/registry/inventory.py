"""Inventory native Hermes skills from the filesystem (authoritative for install_state)."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from agent_os import DEFAULT_HERMES_HOME

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        out[key.strip()] = val.strip().strip("\"'")
    return out


def _skill_id_from_path(rel: Path) -> str:
    # Prefer directory name containing SKILL.md
    return rel.parent.name


def inventory_skills(hermes_home: Path | None = None) -> list[dict[str, Any]]:
    home = hermes_home or DEFAULT_HERMES_HOME
    skills_root = home / "skills"
    entries: list[dict[str, Any]] = []
    if not skills_root.is_dir():
        return entries
    for skill_md in sorted(skills_root.rglob("SKILL.md")):
        if any(part.startswith(".") for part in skill_md.relative_to(skills_root).parts):
            continue
        rel = skill_md.relative_to(skills_root)
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        fm = _parse_frontmatter(text)
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        skill_id = fm.get("name") or _skill_id_from_path(rel)
        category = str(rel.parts[0]) if len(rel.parts) > 2 else (
            str(rel.parts[0]) if len(rel.parts) == 2 and rel.parts[0] != skill_id else ""
        )
        # category/skill/SKILL.md → category = first part when depth>=2
        if len(rel.parts) >= 2:
            category = "/".join(rel.parts[:-2]) if len(rel.parts) > 2 else (
                rel.parts[0] if rel.parts[0] != skill_id else ""
            )
            if len(rel.parts) == 2:
                # skill/SKILL.md at top
                category = ""
            elif len(rel.parts) >= 3:
                category = "/".join(rel.parts[:-2]) if len(rel.parts) > 3 else rel.parts[0]
        entries.append(
            {
                "skill_id": skill_id,
                "display_name": skill_id,
                "description": fm.get("description", ""),
                "native_path": str(skill_md),
                "relative_path": str(rel),
                "category": category,
                "source": "local" if category == "" and "official" not in text[:200] else "local",
                "source_type": "DERIVED",
                "content_hash": content_hash,
                "install_state": "installed",
                "trust_tier": "T0" if skill_id.startswith("agent-os") else "T1",
                "learned": "learned" in rel.parts,
            }
        )
    # Deduplicate by skill_id preferring longer paths (more specific)
    by_id: dict[str, dict[str, Any]] = {}
    for e in entries:
        prev = by_id.get(e["skill_id"])
        if not prev or len(e["relative_path"]) >= len(prev["relative_path"]):
            by_id[e["skill_id"]] = e
    return [by_id[k] for k in sorted(by_id)]
