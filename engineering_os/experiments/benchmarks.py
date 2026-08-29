"""Versioned fixture benchmark suites."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from engineering_os.experiments.config_snapshot import hash_tree

ROOT = Path(__file__).resolve().parents[2]
SUITE_ROOT = ROOT / "experiments" / "benchmarks"
FIXTURE_SRC = ROOT / "tests" / "evaluation" / "fixture_src"


def load_suite(suite_id: str) -> dict[str, Any]:
    path = SUITE_ROOT / f"{suite_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(path)
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("benchmark suite must be a mapping")
    return data


def materialize_real_case(case: dict[str, Any], dest: Path) -> dict[str, Any]:
    case_id = str(case.get("case_id") or case.get("artifact") or "")
    variant = str(case.get("tree") or case.get("artifact") or "broken")
    if variant not in {"broken", "golden"}:
        variant = "broken"
    source = SUITE_ROOT / "real-v1" / case_id / variant
    if not source.is_dir():
        raise FileNotFoundError(source)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source, dest)
    tree = hash_tree(dest)
    return {"path": str(dest), "artifact": variant, "case_id": case_id, "tree_hash": tree["tree_hash"]}


def materialize_case(case: dict[str, Any], dest: Path) -> dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    kind = case.get("artifact") or "clean"
    suite = str(case.get("suite") or case.get("benchmark_suite") or "")
    if suite.startswith("real-") or str(case.get("source") or "") == "real-v1":
        return materialize_real_case(case, dest)
    if dest.exists():
        for child in dest.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    shutil.copytree(FIXTURE_SRC, dest, dirs_exist_ok=True)
    app = dest / "src" / "app.py"
    if kind == "broken":
        app.write_text("def add(left, right):\n    return left - right\n", encoding="utf-8")
    elif kind == "clean":
        app.write_text("def add(left, right):\n    return left + right\n", encoding="utf-8")
    else:
        raise ValueError(f"unknown artifact {kind}")
    tree = hash_tree(dest)
    return {"path": str(dest), "artifact": kind, "tree_hash": tree["tree_hash"]}


def default_cases(n: int, artifact: str, suite: str = "fixture-v1") -> list[dict[str, Any]]:
    return [
        {
            "case_id": f"{suite}-case-{index:02d}",
            "pair_id": f"{suite}-pair-{index:02d}",
            "stratum": suite,
            "artifact": artifact,
            "suite": suite,
        }
        for index in range(1, n + 1)
    ]
