#!/usr/bin/env python3
"""Expand curated sources via Hermes Hub search/inspect — no installs here."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for p in [cur, *cur.parents]:
        if (p / "plugin.yaml").is_file() and (p / "pyproject.toml").is_file() and (p / "agent_os").is_dir():
            return p
    raise RuntimeError("repo root not found")
ROOT = _repo_root()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/ubuntu/.hermes/hermes-agent")

from agent_os.registry.sources_util import allowlisted_repos  # noqa: E402

QUERIES = [
    "solidity security audit",
    "solidity",
    "monad",
    "monskills",
    "interview jtbd",
    "jobs to be done",
    "testing business ideas",
    "founder playbook",
    "ai engineering",
    "product manager",
    "hackathon",
    "startup validation",
    "web3 security",
]


def hub_search(query: str, limit: int = 15) -> list[dict]:
    proc = subprocess.run(
        ["hermes", "skills", "search", query, "--json", "--limit", str(limit)],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.get("results") or data.get("items") or [])
    return []


def main() -> None:
    allow = allowlisted_repos()
    seen: dict[str, dict] = {}
    for q in QUERIES:
        for hit in hub_search(q):
            ident = hit.get("identifier") or ""
            if not ident:
                continue
            prev = seen.get(ident)
            if prev is None:
                seen[ident] = {
                    "identifier": ident,
                    "name": hit.get("name"),
                    "source": hit.get("source"),
                    "trust_level": hit.get("trust_level") or hit.get("trust"),
                    "description": (hit.get("description") or "")[:300],
                    "queries": [q],
                    "allowlisted_repo_match": any(
                        r.lower() in ident.lower() for r in allow
                    ),
                }
            else:
                if q not in prev["queries"]:
                    prev["queries"].append(q)

    # Try inspect for allowlisted repos and top hits mentioning allowlist owners
    try:
        from hermes_cli.skills_hub import inspect_skill
    except Exception as exc:  # pragma: no cover
        inspect_skill = None
        inspect_err = str(exc)
    else:
        inspect_err = None

    inspect_results = []
    candidates = sorted(seen.values(), key=lambda x: (not x["allowlisted_repo_match"], x["identifier"]))
    for hit in candidates[:40]:
        row = {"identifier": hit["identifier"], "from_search": hit}
        if inspect_skill is None:
            row["inspect_error"] = inspect_err
        else:
            try:
                meta = inspect_skill(hit["identifier"])
                row["found"] = bool(meta)
                if meta:
                    row["meta"] = {
                        k: meta.get(k)
                        for k in ("name", "description", "source", "identifier", "tags")
                    }
            except Exception as exc:
                row["found"] = False
                row["inspect_error"] = str(exc)[:300]
        inspect_results.append(row)

    out = {
        "allowlisted_repos": sorted(allow),
        "search_hit_count": len(seen),
        "search_hits": [seen[k] for k in sorted(seen)],
        "inspect": inspect_results,
        "inspect_import_error": inspect_err,
    }
    dest = ROOT / "tests/evidence/agent-os-hub-ingest.json"
    dest.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {dest} hits={len(seen)}")
    # Print allowlisted matches
    matched = [h for h in seen.values() if h["allowlisted_repo_match"]]
    print(f"allowlisted_matches={len(matched)}")
    for m in matched:
        print(m["trust_level"], m["source"], m["identifier"])


if __name__ == "__main__":
    main()
