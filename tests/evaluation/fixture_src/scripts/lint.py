#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "LINT_VIOLATION"
root = Path(__file__).resolve().parents[1]
hits = []
for path in root.rglob("*.py"):
    if "scripts" in path.parts:
        continue
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        hits.append(str(path.relative_to(root)))
if hits:
    print("lint violations:", ", ".join(hits))
    sys.exit(1)
print("lint clean")
