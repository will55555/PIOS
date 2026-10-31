from __future__ import annotations

import sys
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from pios_algo.events import Envelope, EventType, Meta  # noqa: E402

NY = ZoneInfo("America/New_York")


@pytest.fixture
def make_event():
    def _make(**overrides):
        base = dict(
            tenant_id="will",
            stream="trade",
            stream_id="MOM-01#2026-11-02#AAPL",
            type=EventType.SignalDetected,
            ts=datetime(2026, 11, 2, 10, 45, tzinfo=NY),
            payload={"symbol": "AAPL", "close": 348.82},
            meta=Meta(source="engine", strategy="MOM-01", mode="paper", autonomy_level="L0"),
        )
        base.update(overrides)
        return Envelope(**base)

    return _make


@pytest.fixture
def risk_id() -> uuid.UUID:
    return uuid.uuid4()
