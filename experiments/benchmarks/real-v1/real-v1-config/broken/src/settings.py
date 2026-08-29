import json
from pathlib import Path

def timeout() -> int:
    data = json.loads((Path(__file__).resolve().parents[1] / "config" / "app.json").read_text())
    return int(data["timeout_seconds"])
