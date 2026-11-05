"""Event envelope v1 (architecture v0.5 §3; build step 1 brief §3).

The envelope is the cross-language contract (ADR-001 §5): its JSON Schema is
exported to ``schemas/event-envelope.v1.json`` and a test fails on drift.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from pios_algo.tenancy import TENANT_ID_RE

ENVELOPE_VERSION = 1


class EventType(StrEnum):
    # Core types (architecture §3)
    SignalDetected = "algo.SignalDetected"
    SignalBlocked = "algo.SignalBlocked"
    RiskCheckPassed = "algo.RiskCheckPassed"
    OrderPlaced = "algo.OrderPlaced"
    OrderAcknowledged = "algo.OrderAcknowledged"
    OrderConfirmed = "algo.OrderConfirmed"
    OrderPartiallyFilled = "algo.OrderPartiallyFilled"
    OrderFilled = "algo.OrderFilled"
    OrderRejected = "algo.OrderRejected"
    OrderRevoked = "algo.OrderRevoked"
    StopHit = "algo.StopHit"
    TargetHit = "algo.TargetHit"
    TimeExit = "algo.TimeExit"
    PositionClosed = "algo.PositionClosed"
    DeviationLogged = "algo.DeviationLogged"
    SleeveFunded = "algo.SleeveFunded"
    KillSwitchTripped = "algo.KillSwitchTripped"
    KillSwitchReset = "algo.KillSwitchReset"
    DailyLimitHit = "algo.DailyLimitHit"
    AccountLimitHit = "algo.AccountLimitHit"
    FreezeSet = "algo.FreezeSet"
    FreezeLifted = "algo.FreezeLifted"
    HostInterrupted = "algo.HostInterrupted"
    HostRecovered = "algo.HostRecovered"
    FallbackEngaged = "algo.FallbackEngaged"
    InfraCostRecorded = "algo.InfraCostRecorded"
    HostingTierChanged = "algo.HostingTierChanged"
    BoundViolationBlocked = "algo.BoundViolationBlocked"
    AutonomyLevelChanged = "algo.AutonomyLevelChanged"
    # Journal types (added in step 1 so day-1 history imports without loss)
    AccountSnapshot = "algo.AccountSnapshot"
    DecisionRecorded = "algo.DecisionRecorded"
    ConfigChanged = "algo.ConfigChanged"
    PositionChecked = "algo.PositionChecked"
    ResultRecorded = "algo.ResultRecorded"
    AnalysisRecorded = "algo.AnalysisRecorded"
    NoteRecorded = "algo.NoteRecorded"


# Only Will (the tenant) may emit these (architecture §2A/§2D; ADR-002 A6).
TENANT_ONLY_TYPES = frozenset(
    {
        EventType.AutonomyLevelChanged,
        EventType.FreezeSet,
        EventType.FreezeLifted,
        EventType.KillSwitchReset,
    }
)

Stream = Literal["trade", "sleeve", "system", "signal"]
Source = Literal["engine", "lambda", "claude", "will"]
Mode = Literal["live", "paper", "shadow", "backtest"]
AutonomyLevel = Literal["L0", "L1", "L2", "L3"]
Host = Literal["spot", "ondemand", "lambda", "claude", "local"]


def _find_non_finite(value: Any, path: str = "payload") -> str | None:
    """Return the path of the first NaN/inf float inside ``value``, else None."""
    if isinstance(value, float) and not math.isfinite(value):
        return path
    if isinstance(value, dict):
        for k, v in value.items():
            hit = _find_non_finite(v, f"{path}.{k}")
            if hit:
                return hit
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            hit = _find_non_finite(v, f"{path}[{i}]")
            if hit:
                return hit
    return None


class Meta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: Source
    strategy: str | None = None
    strategy_version: str | None = None
    param_hash: str | None = None
    sleeve: str | None = None
    mode: Mode | None = None
    autonomy_level: AutonomyLevel | None = None
    rule_ref: str | None = None
    risk_check_id: uuid.UUID | None = None
    host: Host | None = None
    broker: str | None = None
    account: str | None = None


class Envelope(BaseModel):
    """One immutable event. Append-only; never edited after it is stored."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    tenant_id: str = Field(pattern=TENANT_ID_RE.pattern)
    stream: Stream
    stream_id: str = Field(min_length=1)
    type: EventType
    version: int = Field(default=ENVELOPE_VERSION, ge=1)
    ts: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    meta: Meta
    # Event chain (PIOS ADR-011, ADR-020); stored events can't be backfilled, so the fields exist from the start.
    correlation_id: uuid.UUID | None = None
    causation_id: uuid.UUID | None = None

    @field_validator("ts")
    @classmethod
    def _ts_must_be_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("ts must be timezone-aware")
        return v

    @model_validator(mode="after")
    def _rules(self) -> Envelope:
        hit = _find_non_finite(self.payload)
        if hit:
            raise ValueError(f"non-finite number at {hit} (architecture §2C indicator validity)")
        if self.type in TENANT_ONLY_TYPES and self.meta.source != "will":
            raise ValueError(f"{self.type.value} may only be emitted by source='will'")
        if (
            self.type is EventType.OrderPlaced
            and self.meta.mode in ("live", "paper")
            and self.meta.risk_check_id is None
            and not self._is_legacy_import()
        ):
            raise ValueError("OrderPlaced in live/paper mode requires meta.risk_check_id (architecture §2C)")
        return self

    def _is_legacy_import(self) -> bool:
        # Day-1 history predates the risk engine; allowed only when clearly flagged.
        return self.meta.source == "claude" and self.payload.get("imported") is True

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str) -> Envelope:
        return cls.model_validate_json(raw)


def export_json_schema() -> dict[str, Any]:
    schema = Envelope.model_json_schema()
    schema["$id"] = "https://terra/pios-algo/schemas/event-envelope.v1.json"
    schema["title"] = "pios-algo event envelope v1"
    return schema
