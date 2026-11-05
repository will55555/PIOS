"""Upcaster for the day-1 legacy JSONL (claude/mom01-events/*.jsonl) → Envelope v1.

Rules (build step 1 brief §6):
- add ``tenant_id``; naive timestamps are America/New_York;
- ``source`` = ``will`` for user-originated lines (``user*`` types), else ``claude``;
- the original line is kept verbatim under ``payload.legacy``;
- event_id is deterministic (uuid5 of tenant + line) so a re-import adds nothing;
- legacy types with no mapping → ``DeviationLogged`` on the system stream, ``payload.legacy_type`` set.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from pios_algo.events.envelope import Envelope, EventType, Meta

NY = ZoneInfo("America/New_York")
IMPORT_NAMESPACE = uuid.UUID("6f1c2f3e-6a43-4c8e-9a51-1d0b8f0a2c01")

# legacy type -> (EventType, stream)
LEGACY_MAP: dict[str, tuple[EventType, str]] = {
    "signal": (EventType.SignalDetected, "signal"),
    "signal_blocked": (EventType.SignalBlocked, "signal"),
    "signal_not_taken": (EventType.SignalBlocked, "signal"),
    "order_instruction": (EventType.OrderPlaced, "trade"),
    "fill": (EventType.OrderFilled, "trade"),
    "order_revoked": (EventType.OrderRevoked, "trade"),
    "stop_hit": (EventType.StopHit, "trade"),
    "position_check": (EventType.PositionChecked, "trade"),
    "deviation": (EventType.DeviationLogged, "system"),
    "account": (EventType.AccountSnapshot, "sleeve"),
    "user_decision": (EventType.DecisionRecorded, "system"),
    "rule_change": (EventType.DecisionRecorded, "system"),
    "user_correction": (EventType.DecisionRecorded, "system"),
    "config_change": (EventType.ConfigChanged, "system"),
    "setup": (EventType.ConfigChanged, "system"),
    "shadow_result": (EventType.ResultRecorded, "signal"),
    "eod_comparison": (EventType.ResultRecorded, "trade"),
    "day_summary": (EventType.ResultRecorded, "system"),
    "analysis": (EventType.AnalysisRecorded, "system"),
    "backtest": (EventType.AnalysisRecorded, "system"),
    "finding": (EventType.AnalysisRecorded, "system"),
    "review": (EventType.AnalysisRecorded, "system"),
    "design": (EventType.NoteRecorded, "system"),
    "build": (EventType.NoteRecorded, "system"),
    "bug_fix": (EventType.NoteRecorded, "system"),
    "repair": (EventType.NoteRecorded, "system"),
    "tokens": (EventType.NoteRecorded, "system"),
    "run": (EventType.NoteRecorded, "system"),
    "user": (EventType.NoteRecorded, "system"),
    "user_action": (EventType.NoteRecorded, "system"),
    "context": (EventType.NoteRecorded, "system"),
    "universe": (EventType.NoteRecorded, "system"),
    "opening_range": (EventType.NoteRecorded, "system"),
}


@dataclass(frozen=True)
class ImportReport:
    lines_in: int
    events_out: int
    unmapped_types: dict[str, int]
    by_type: dict[str, int]


def parse_ts(raw: str) -> datetime:
    ts = datetime.fromisoformat(raw)
    return ts.replace(tzinfo=NY) if ts.tzinfo is None else ts


def _symbol(line: dict[str, Any]) -> str | None:
    fields = line.get("fields")
    sym = line.get("symbol") or (fields.get("ticker") if isinstance(fields, dict) else None)
    return str(sym) if sym else None


def upcast_line(raw_line: str, tenant_id: str, default_strategy: str = "MOM-01") -> Envelope:
    line = json.loads(raw_line)
    legacy_type = str(line.get("type", "unknown"))
    mapped = LEGACY_MAP.get(legacy_type)
    if mapped is None:
        etype, stream = EventType.DeviationLogged, "system"
    else:
        etype, stream = mapped

    ts = parse_ts(line["ts"])
    day = ts.date().isoformat()
    strategy = line.get("strategy") or default_strategy
    if strategy == "ALL":
        strategy = None
    symbol = _symbol(line)

    if stream in ("trade", "signal"):
        stream_id = f"{strategy or 'ALL'}#{day}#{symbol or 'NA'}"
    else:
        stream_id = f"{stream}#{day}"

    source = "will" if legacy_type == "user" or legacy_type.startswith("user_") else "claude"
    payload: dict[str, Any] = {"imported": True, "legacy_type": legacy_type, "legacy": line}
    if symbol:
        payload["symbol"] = symbol

    meta = Meta(
        source=source,
        strategy=strategy,
        mode="live" if etype in (EventType.OrderPlaced, EventType.OrderFilled, EventType.OrderRevoked) else None,
        autonomy_level="L2" if stream == "trade" else None,
        rule_ref=line.get("rule_ref"),
        host="claude",
        broker="webull",
    )
    event_id = uuid.uuid5(IMPORT_NAMESPACE, f"{tenant_id}|{raw_line.strip()}")
    return Envelope(
        event_id=event_id,
        tenant_id=tenant_id,
        stream=stream,
        stream_id=stream_id,
        type=etype,
        ts=ts,
        payload=payload,
        meta=meta,
    )


def upcast_file(path: Path | str, tenant_id: str) -> tuple[list[Envelope], ImportReport]:
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    events = [upcast_line(ln, tenant_id) for ln in lines]
    unmapped: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for env in events:
        by_type[env.type.value] = by_type.get(env.type.value, 0) + 1
        lt = env.payload["legacy_type"]
        if lt not in LEGACY_MAP:
            unmapped[lt] = unmapped.get(lt, 0) + 1
    return events, ImportReport(len(lines), len(events), unmapped, by_type)


def iter_unique_types(path: Path | str) -> Iterable[str]:
    seen: set[str] = set()
    for ln in Path(path).read_text(encoding="utf-8").splitlines():
        if ln.strip():
            t = json.loads(ln).get("type", "unknown")
            if t not in seen:
                seen.add(t)
                yield t
