"""Write schemas/event-envelope.v1.json from the Envelope model (the cross-language contract)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pios_algo.events import export_json_schema  # noqa: E402

SCHEMA_PATH = ROOT / "schemas" / "event-envelope.v1.json"


def render() -> str:
    return json.dumps(export_json_schema(), indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    SCHEMA_PATH.write_text(render(), encoding="utf-8")
    print(f"wrote {SCHEMA_PATH}")
