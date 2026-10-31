from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from pios.events import Envelope, EventSource


@pytest.fixture
def make_event() -> Callable[..., Envelope]:
    def _make(**overrides: Any) -> Envelope:
        now = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
        fields: dict[str, Any] = {
            "tenant_id": "will",
            "aggregate_type": "test",
            "aggregate_id": "test-1",
            "type": "TestEvent",
            "schema_version": 1,
            "occurred_at": now,
            "recorded_at": now,
            "source": EventSource(adapter="test", version="1"),
            "idempotency_key": "test:1",
            "correlation_id": uuid.uuid4(),
        }
        return Envelope(**{**fields, **overrides})

    return _make
