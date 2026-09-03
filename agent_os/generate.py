"""Build machine registry + SKILLS.md from inventory + curated sources."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from agent_os import DEFAULT_HERMES_HOME, REGISTRY_DIR, POLICIES_DIR
from agent_os.inventory import inventory_skills
from agent_os.schema import validate_skill_entry


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    assert isinstance(data, dict)
    return data


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _capability_category(caps: list[str], domains: list[str]) -> str:
    mapping = [
        (("ai-engineering", "math-foundations"), "AI Engineering"),
        (("jtbd", "customer-discovery"), "Product"),
        (("assumption-testing", "startup-validation", "adversarial-review"), "Startup"),
        (("pitch-storytelling",), "Pitch"),
        (("solidity-audit", "security-audit"), "Security"),
        (("monad-routing", "monad-implementation", "monad-execution", "monad-development"), "Monad"),
        (("web3-security", "web3-testing", "agentic-web3"), "Web3"),
        (("frontend-nextjs",), "Frontend"),
        (("temporal-workflows",), "Backend"),
        (("design-system",), "Design"),
    ]
    capset = set(caps)
    for keys, label in mapping:
        if capset & set(keys):
            return label
    if "hackathon" in domains:
        return "Hackathon"
    if "research" in domains:
        return "Research"
    return "Meta / Agent OS"


def build_registry(hermes_home: Path | None = None) -> dict[str, Any]:
    home = hermes_home or DEFAULT_HERMES_HOME
    sources_doc = _load_yaml(REGISTRY_DIR / "sources.yaml")
    trust_doc = _load_yaml(POLICIES_DIR / "trust-policy.yaml")
    mutable_doc = _load_yaml(POLICIES_DIR / "mutable-fact-policy.yaml")
    annotations = (_load_yaml(REGISTRY_DIR / "annotations.yaml").get("skills") or {})
    installed = inventory_skills(home)

    # Ensure GitHub expansion cache exists when evidence is present
    expanded_path = REGISTRY_DIR / "github-expanded.json"
    if not expanded_path.exists():
        try:
            from agent_os.ingest_github import write_expanded_cache

            write_expanded_cache()
        except Exception:
            pass
    expanded_doc = {}
    if expanded_path.exists():
        import json as _json

        expanded_doc = _json.loads(expanded_path.read_text(encoding="utf-8"))


    skills: dict[str, dict[str, Any]] = {}
    for e in installed:
        skill_id = e["skill_id"]
        domains: list[str] = []
        caps: list[str] = []
        # Heuristic DERIVED caps from path/name — tagged DERIVED
        name = skill_id.lower()
        rel = e.get("relative_path", "").lower()
        if "design" in name or "design" in rel:
            domains.append("design")
            caps.append("design-system")
        if "test-driven" in name or "systematic-debugging" in name:
            domains.append("testing")
            caps.append("software-testing")
        if "github" in rel:
            domains.append("devops")
            caps.append("github-workflow")
        if name == "find-skills":
            caps.append("skill-discovery-npx")
            # negative for hermes hub path
        if name == "agent-reach":
            caps.append("web-research")
            domains.append("research")
        entry = {
            "skill_id": skill_id,
            "display_name": e["display_name"],
            "description": e["description"],
            "native_path": e["native_path"],
            "source": e["source"],
            "source_type": "local-filesystem",
            "repository": "",
            "upstream_identifier": "",
            "version": "",
            "content_hash": e["content_hash"],
            "install_state": "installed",
            "trust_tier": e["trust_tier"],
            "security_state": "local",
            "category": _capability_category(caps, domains),
            "domains": domains,
            "capabilities": caps,
            "task_types": [],
            "triggers": [skill_id.replace("-", " ")],
            "negative_triggers": ["npx skills add"] if skill_id == "find-skills" else [],
            "when_to_use": [e["description"][:200]] if e["description"] else [],
            "when_not_to_use": [],
            "risk_domains": [],
            "dependencies": [],
            "related_skills": [],
            "complements": [],
            "supersedes": [],
            "fallbacks": [],
            "bundle_membership": [],
            "profile_scope": "default",
            "mutable_fact_policy": None,
            "last_inspected": "",
            "last_updated": "",
            "local_modification_state": "unknown",
            "field_kinds": {
                "skill_id": "DERIVED",
                "description": "DERIVED",
                "capabilities": "DERIVED",
                "domains": "DERIVED",
                "trust_tier": "DERIVED",
                "install_state": "DERIVED",
            },
        }
        # Apply CURATED annotations overlay
        ann = annotations.get(skill_id) or {}
        if ann:
            for key in (
                "capabilities",
                "domains",
                "task_types",
                "triggers",
                "negative_triggers",
                "when_to_use",
                "when_not_to_use",
                "trust_tier",
                "security_state",
            ):
                if key in ann and ann[key] is not None:
                    if key in ("capabilities", "domains", "task_types", "triggers", "negative_triggers"):
                        entry[key] = sorted(set(list(entry.get(key) or []) + list(ann[key] or [])))
                    else:
                        entry[key] = ann[key]
                    entry["field_kinds"][key] = "CURATED"
            entry["category"] = _capability_category(entry.get("capabilities") or [], entry.get("domains") or [])
        skills[skill_id] = entry

    # Curated source stubs (per-repo until expanded to real skill IDs)
    for src in sources_doc.get("sources", []) or []:
        repo = src.get("repository", "")
        caps = list(src.get("capabilities") or [])
        domains = list(src.get("domains") or [])
        # Synthetic skill_id for unexpanded repo — UNKNOWN skill enumeration
        stub_id = repo.replace("/", "--").lower() if repo else src.get("id")
        if stub_id in skills:
            # Enrich installed collision (e.g. design-md)
            skills[stub_id]["repository"] = repo
            skills[stub_id]["trust_tier"] = src.get("trust_tier", skills[stub_id]["trust_tier"])
            continue
        # Match installed design-md to nolly source
        if src.get("id") == "nolly-studio-design-md" and "design-md" in skills:
            skills["design-md"]["repository"] = repo
            skills["design-md"]["trust_tier"] = "T3"
            skills["design-md"]["security_state"] = "reverify_required"
            skills["design-md"]["field_kinds"]["trust_tier"] = "CURATED"
            skills["design-md"]["capabilities"] = sorted(
                set(skills["design-md"].get("capabilities") or []) | set(caps or ["design-system"])
            )
            continue

        seed_caps = caps
        for seed in sources_doc.get("capability_seeds", []) or []:
            if seed.get("capability") in caps:
                # attach triggers later on capability map
                pass

        entry = {
            "skill_id": stub_id,
            "display_name": src.get("id", stub_id),
            "description": src.get("notes") or f"Curated source {repo} (per-skill expansion pending/UNKNOWN)",
            "native_path": "",
            "source": repo,
            "source_type": "curated-repository",
            "repository": repo,
            "upstream_identifier": repo,
            "version": "",
            "content_hash": "",
            "install_state": "not_installed",
            "trust_tier": src.get("trust_tier", "T3"),
            "security_state": "reverify_required" if src.get("reverify_before_trust") else "uninspected",
            "category": _capability_category(seed_caps, domains),
            "domains": domains,
            "capabilities": seed_caps,
            "task_types": [],
            "triggers": [c.replace("-", " ") for c in seed_caps],
            "negative_triggers": [],
            "when_to_use": [f"When capability in {seed_caps} is required"],
            "when_not_to_use": ["Before source re-verification"] if src.get("reverify_before_trust") else [],
            "risk_domains": domains,
            "dependencies": [],
            "related_skills": [],
            "complements": [],
            "supersedes": [],
            "fallbacks": [],
            "bundle_membership": [],
            "profile_scope": "default",
            "mutable_fact_policy": src.get("mutable_fact_policy"),
            "last_inspected": "",
            "last_updated": "",
            "local_modification_state": "n/a",
            "field_kinds": {
                "skill_id": "CURATED",
                "capabilities": "CURATED" if seed_caps else "UNKNOWN",
                "trust_tier": "CURATED",
                "install_state": "DERIVED",
                "description": "CURATED",
            },
            "source_meta": {"category": src.get("category"), "id": src.get("id")},
        }
        # Also emit capability-virtual skills for routing when caps listed
        skills[stub_id] = entry
        for cap in seed_caps:
            virt_id = f"capability:{cap}"
            if virt_id not in skills:
                seed = next(
                    (s for s in (sources_doc.get("capability_seeds") or []) if s.get("capability") == cap),
                    {},
                )
                skills[virt_id] = {
                    "skill_id": virt_id,
                    "display_name": cap,
                    "description": f"Virtual capability node for {cap} (CURATED seed)",
                    "native_path": "",
                    "source": repo,
                    "source_type": "capability-seed",
                    "repository": repo,
                    "upstream_identifier": "",
                    "version": "",
                    "content_hash": "",
                    "install_state": "virtual",
                    "trust_tier": src.get("trust_tier", "T2"),
                    "security_state": "n/a",
                    "category": _capability_category([cap], list(seed.get("domains") or domains)),
                    "domains": list(seed.get("domains") or domains),
                    "capabilities": [cap],
                    "task_types": list(seed.get("task_types") or []),
                    "triggers": list(seed.get("triggers") or [cap.replace("-", " ")]),
                    "negative_triggers": list(seed.get("negative_triggers") or []),
                    "when_to_use": [f"Tasks needing {cap}"],
                    "when_not_to_use": list(seed.get("negative_triggers") or []),
                    "risk_domains": [],
                    "dependencies": [],
                    "related_skills": [stub_id],
                    "complements": [],
                    "supersedes": [],
                    "fallbacks": [],
                    "bundle_membership": [],
                    "profile_scope": "default",
                    "mutable_fact_policy": src.get("mutable_fact_policy"),
                    "last_inspected": "",
                    "last_updated": "",
                    "local_modification_state": "n/a",
                    "field_kinds": {
                        "skill_id": "CURATED",
                        "capabilities": "CURATED",
                        "triggers": "CURATED",
                        "install_state": "DERIVED",
                    },
                }

    # Merge per-skill GitHub tree expansion (356 skills etc.)
    installed_names = {e["skill_id"] for e in installed}
    for row in expanded_doc.get("skills") or []:
        upstream = row.get("upstream_identifier") or ""
        unique = upstream.replace("/", "--") if upstream else row.get("skill_id")
        short = row.get("skill_id")
        # If already installed under short name, enrich rather than duplicate
        if short in skills and skills[short].get("install_state") == "installed":
            skills[short]["repository"] = skills[short].get("repository") or row.get("repository")
            skills[short]["upstream_identifier"] = upstream
            skills[short]["field_kinds"]["repository"] = "DERIVED"
            continue
        if unique in skills:
            continue
        entry = {
            "skill_id": unique,
            "display_name": short,
            "description": row.get("description") or "",
            "native_path": "",
            "source": row.get("repository") or "",
            "source_type": "github-tree",
            "repository": row.get("repository") or "",
            "upstream_identifier": upstream,
            "version": "",
            "content_hash": "",
            "install_state": "not_installed" if short not in installed_names else "installed",
            "trust_tier": row.get("trust_tier") or "T3",
            "security_state": row.get("security_state") or "uninspected",
            "category": _capability_category([], []),
            "domains": list(row.get("domains") or []),
            "capabilities": list(row.get("capabilities") or []),
            "task_types": [],
            "triggers": list(row.get("triggers") or []),
            "negative_triggers": list(row.get("negative_triggers") or []),
            "when_to_use": list(row.get("when_to_use") or []),
            "when_not_to_use": list(row.get("when_not_to_use") or []),
            "risk_domains": [],
            "dependencies": [],
            "related_skills": [],
            "complements": [],
            "supersedes": [],
            "fallbacks": [],
            "bundle_membership": [],
            "profile_scope": "default",
            "mutable_fact_policy": None,
            "last_inspected": "",
            "last_updated": "",
            "local_modification_state": "n/a",
            "raw_url": row.get("raw_url") or "",
            "path": row.get("path") or "",
            "field_kinds": row.get("field_kinds")
            or {
                "skill_id": "DERIVED",
                "trust_tier": "CURATED",
                "install_state": "DERIVED",
            },
        }
        skills[unique] = entry

    skill_list = [skills[k] for k in sorted(skills)]
    for e in skill_list:
        errs = validate_skill_entry(e)
        if errs:
            e.setdefault("validation_errors", errs)

    # Capability map
    cap_map: dict[str, dict[str, Any]] = {}
    for e in skill_list:
        for c in e.get("capabilities") or []:
            cap_map.setdefault(
                c,
                {"capability": c, "skills": [], "installed_skills": [], "virtual_skills": []},
            )
            cap_map[c]["skills"].append(e["skill_id"])
            if e.get("install_state") == "installed":
                cap_map[c]["installed_skills"].append(e["skill_id"])
            if e.get("source_type") == "capability-seed":
                cap_map[c]["virtual_skills"].append(e["skill_id"])
    for c in cap_map:
        cap_map[c]["skills"] = sorted(set(cap_map[c]["skills"]))
        cap_map[c]["installed_skills"] = sorted(set(cap_map[c]["installed_skills"]))
        cap_map[c]["virtual_skills"] = sorted(set(cap_map[c]["virtual_skills"]))

    lock = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hermes_home": str(home),
        "installed_count": sum(1 for e in skill_list if e.get("install_state") == "installed"),
        "entries": {
            e["skill_id"]: {
                "content_hash": e.get("content_hash", ""),
                "trust_tier": e.get("trust_tier"),
                "install_state": e.get("install_state"),
                "repository": e.get("repository", ""),
            }
            for e in skill_list
        },
    }

    # Registry body is timestamp-free for idempotent checksums; stamp lives in lock + evidence.
    registry = {
        "version": 1,
        "skills": skill_list,
        "trust_policy_fingerprint": hashlib.sha256(
            (POLICIES_DIR / "trust-policy.yaml").read_bytes()
        ).hexdigest()
        if (POLICIES_DIR / "trust-policy.yaml").exists()
        else "",
        "mutable_fact_policy": mutable_doc,
        "sources_fingerprint": hashlib.sha256(
            (REGISTRY_DIR / "sources.yaml").read_bytes()
        ).hexdigest()
        if (REGISTRY_DIR / "sources.yaml").exists()
        else "",
        "trust_doc_keys": sorted((trust_doc.get("tiers") or {}).keys()),
    }
    return {
        "registry": registry,
        "capability_map": {"version": 1, "capabilities": dict(sorted(cap_map.items()))},
        "lock": lock,
        "skills": skill_list,
    }


def render_skills_md(skill_list: list[dict[str, Any]]) -> str:
    header = """# Hermes Agent OS Global Capability Manifest

Generated artifact.
Native skills remain owned by Hermes skill directories.
Do not hand-edit; regenerate from the registry.

"""
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for e in skill_list:
        if e.get("source_type") == "capability-seed":
            continue  # human doc focuses on real/curated skills
        cat = e.get("category") or "Meta / Agent OS"
        by_cat.setdefault(cat, []).append(e)
    lines = [header]
    for cat in sorted(by_cat):
        lines.append(f"## {cat}\n")
        for e in sorted(by_cat[cat], key=lambda x: x["skill_id"]):
            lines.append(f"### {e['skill_id']}")
            lines.append("")
            lines.append(f"- **What:** {e.get('description') or '(no description)'}")
            lines.append(f"- **Skill ID:** `{e['skill_id']}`")
            lines.append(f"- **Source:** {e.get('repository') or e.get('source')}")
            lines.append(f"- **Install:** {e.get('install_state')}")
            lines.append(f"- **Trust:** {e.get('trust_tier')} ({e.get('security_state')})")
            lines.append(f"- **When to use:** {'; '.join(e.get('when_to_use') or ['—'])}")
            lines.append(f"- **When not:** {'; '.join(e.get('when_not_to_use') or e.get('negative_triggers') or ['—'])}")
            lines.append(f"- **Capabilities:** {', '.join(e.get('capabilities') or []) or '—'}")
            lines.append(f"- **Complements:** {', '.join(e.get('complements') or e.get('related_skills') or []) or '—'}")
            lines.append(f"- **Path:** `{e.get('native_path') or 'not installed'}`")
            lines.append("")
    return "\n".join(lines) + "\n"


def regenerate(hermes_home: Path | None = None, write_hermes_projection: bool = True) -> dict[str, Any]:
    home = hermes_home or DEFAULT_HERMES_HOME
    built = build_registry(home)
    reg_path = REGISTRY_DIR / "skills.registry.json"
    cap_path = REGISTRY_DIR / "capability-map.json"
    lock_path = REGISTRY_DIR / "skills.lock.json"
    md_path = REGISTRY_DIR / "SKILLS.md"
    for path, obj in (
        (reg_path, built["registry"]),
        (cap_path, built["capability_map"]),
        (lock_path, built["lock"]),
    ):
        _atomic_write(path, json.dumps(obj, indent=2, sort_keys=True) + "\n")
    md = render_skills_md(built["skills"])
    _atomic_write(md_path, md)
    if write_hermes_projection:
        _atomic_write(home / "SKILLS.md", md)
    # checksum evidence
    evidence = {
        "skills_registry_sha256": hashlib.sha256(reg_path.read_bytes()).hexdigest(),
        "skills_md_sha256": hashlib.sha256(md_path.read_bytes()).hexdigest(),
        "installed_count": built["lock"]["installed_count"],
        "total_entries": len(built["skills"]),
    }
    _atomic_write(REGISTRY_DIR / "generate-evidence.json", json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    return evidence
