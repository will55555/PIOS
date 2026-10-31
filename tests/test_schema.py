from __future__ import annotations

import export_schema


def test_committed_schema_matches_model():
    """Fails if the Envelope changed without re-running scripts/export_schema.py."""
    assert export_schema.SCHEMA_PATH.read_text(encoding="utf-8") == export_schema.render()
