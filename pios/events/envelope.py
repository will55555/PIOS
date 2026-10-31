"""PIOS event envelope (ADR-011 correlation chain, ADR-013 versioning, ADR-019 Decision 3, ADR-020)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pios.tenancy import TENANT_ID_RE


class EventSource(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str = Field(min_length=1)
    version: str = Field(min_length=1)


def _find_float(value: Any, path: str = "payload") -> str | None:
    """Return the path of the first float inside ``value``, else None."""
    if isinstance(value, float):
        return path
    if isinstance(value, dict):
        for k, v in value.items():
            hit = _find_float(v, f"{path}.{k}")
            if hit:
                return hit
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            hit = _find_float(v, f"{path}[{i}]")
            if hit:
                return hit
    return None


class Envelope(BaseModel):
    """One immutable event. Append-only; never edited after it is stored."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: str = Field(pattern=TENANT_ID_RE.pattern)
    aggregate_type: str = Field(min_length=1)
    aggregate_id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    schema_version: int = Field(ge=1)
    occurred_at: datetime
    recorded_at: datetime
    source: EventSource
    idempotency_key: str = Field(min_length=1)
    correlation_id: uuid.UUID
    causation_id: uuid.UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at", "recorded_at")
    @classmethod
    def _must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("timestamps must be timezone-aware")
        return v

    @field_validator("payload")
    @classmethod
    def _no_floats(cls, v: dict[str, Any]) -> dict[str, Any]:
        hit = _find_float(v)
        if hit:
            raise ValueError(f"float at {hit}: use integer minor units or a decimal string (ADR-019, ADR-020)")
        return v
