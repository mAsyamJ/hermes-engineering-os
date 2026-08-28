#!/usr/bin/env python3
import ast
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
errors = []
for path in root.rglob("*.py"):
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        errors.append(f"{path.name}: {exc}")
if errors:
    print("typecheck failed:", "; ".join(errors))
    sys.exit(1)
print("typecheck clean")
