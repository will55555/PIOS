from __future__ import annotations

import json
from pathlib import Path

import import_legacy

from pios_algo.events import EventType, SqliteEventStore
from pios_algo.events.upcast import LEGACY_MAP, upcast_file, upcast_line

FIXTURE = Path(__file__).parent / "fixtures" / "legacy-sample.jsonl"


def test_every_line_accounted_for():
    events, report = upcast_file(FIXTURE, "will")
    assert report.lines_in == report.events_out == len(events) > 0
    assert all(e.tenant_id == "will" and e.payload["imported"] is True for e in events)


def test_fixture_covers_every_mapped_type():
    types = {json.loads(ln)["type"] for ln in FIXTURE.read_text().splitlines() if ln.strip()}
    assert set(LEGACY_MAP) <= types


def test_unmapped_type_becomes_deviation():
    env = upcast_line('{"ts":"2026-10-30T09:00","type":"mystery","x":1}', "will")
    assert env.type is EventType.DeviationLogged
    assert env.payload["legacy_type"] == "mystery"


def test_naive_ts_is_new_york():
    env = upcast_line('{"ts":"2026-10-30T09:56","type":"setup"}', "will")
    assert env.ts.utcoffset().total_seconds() == -4 * 3600


def test_user_lines_are_source_will():
    assert upcast_line('{"ts":"2026-10-30T11:23","type":"user_decision","items":[]}', "will").meta.source == "will"
    assert upcast_line('{"ts":"2026-10-30T11:23","type":"analysis"}', "will").meta.source == "claude"


def test_legacy_line_kept_verbatim():
    raw = '{"ts":"2026-10-30T10:40","type":"signal","symbol":"AAPL","close":348.82}'
    env = upcast_line(raw, "will")
    assert env.payload["legacy"] == json.loads(raw)
    assert env.stream_id == "MOM-01#2026-10-30#AAPL"


def test_reimport_adds_nothing(tmp_path):
    assert import_legacy.main([str(FIXTURE), "--root", str(tmp_path)]) == 0
    with SqliteEventStore(tmp_path, "will") as s:
        first = s.count()
    assert import_legacy.main([str(FIXTURE), "--root", str(tmp_path)]) == 0
    with SqliteEventStore(tmp_path, "will") as s:
        assert s.count() == first


def test_fields_may_be_a_string():
    """Regression: the 10/30 opening_range line has "fields" as a string."""
    env = upcast_line('{"ts":"2026-10-30T10:30","type":"opening_range","fields":"[or_low, or_high]"}', "will")
    assert env.type.value == "algo.NoteRecorded"
