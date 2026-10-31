"""Strategy interface + spec schema + approval check (architecture §2 `core/strategy_api`; build step 2).

Tenants implement ``Strategy`` in their own repo (Will: ``will-strategies``) and ship a
versioned JSON spec. The platform only runs a spec whose ``(id, version, param_hash)``
the tenant has approved (planning notes §B; architecture §2C "live vs tested inputs").
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from pios_algo.core.bars import Bar

AutonomyLevel = Literal["L0", "L1", "L2", "L3"]
AssetClass = Literal["us_stock", "crypto"]


class SpecError(ValueError):
    pass


class UnapprovedSpec(SpecError):
    pass


class DesignedOn(BaseModel):
    """Data the rules were designed/fitted on (backtest plan v3 contamination rule)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start: date | None = None
    end: date | None = None
    note: str = ""


class RiskRules(BaseModel):
    """The tenant's own risk rules for this strategy's sleeve (must sit inside platform bounds, ADR-002 A6)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    risk_per_trade_pct: float = Field(gt=0)
    a_plus_risk_pct: float | None = Field(default=None, gt=0)
    kill_switch_pct: float | None = Field(default=None, gt=0, description="drawdown from sleeve high, %")
    monthly_loss_cap_pct: float | None = Field(default=None, gt=0)
    max_concurrent_positions: int = Field(default=1, ge=1)


class StrategySpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(pattern=r"^[A-Z0-9][A-Z0-9-]{1,31}$")
    version: str = Field(min_length=1)
    name: str
    asset_class: AssetClass
    sleeve: str
    autonomy_level: AutonomyLevel
    designed_on: DesignedOn
    expected_signals_per_week: float | None = Field(
        default=None, ge=0, description="from validation; None = not measured yet (blocks live, §2C)"
    )
    risk: RiskRules
    params: dict[str, Any] = Field(default_factory=dict)
    source_ref: str = ""

    @field_validator("params")
    @classmethod
    def _params_finite(cls, v: dict[str, Any]) -> dict[str, Any]:
        def walk(x: Any, path: str) -> None:
            if isinstance(x, float) and not math.isfinite(x):
                raise ValueError(f"non-finite param at {path}")
            if isinstance(x, dict):
                for k, y in x.items():
                    walk(y, f"{path}.{k}")
            elif isinstance(x, list):
                for i, y in enumerate(x):
                    walk(y, f"{path}[{i}]")

        walk(v, "params")
        return v

    @property
    def param_hash(self) -> str:
        """SHA-256 over everything that changes behaviour (all fields except free-text notes)."""
        body = self.model_dump(mode="json", exclude={"name", "source_ref"})
        body["designed_on"].pop("note", None)
        raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode()).hexdigest()

    @property
    def key(self) -> str:
        return f"{self.id}@{self.version}"


def load_spec(path: Path | str) -> StrategySpec:
    try:
        return StrategySpec.model_validate_json(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise SpecError(f"cannot load spec {path}: {e}") from e


@dataclass(frozen=True)
class ApprovedVersion:
    id: str
    version: str
    param_hash: str


def check_approved(spec: StrategySpec, approved: Sequence[ApprovedVersion]) -> None:
    """Refuse any spec whose exact parameters the tenant has not approved."""
    for a in approved:
        if a.id == spec.id and a.version == spec.version:
            if a.param_hash != spec.param_hash:
                raise UnapprovedSpec(f"{spec.key}: param_hash {spec.param_hash[:12]}… != approved {a.param_hash[:12]}…")
            return
    raise UnapprovedSpec(f"{spec.key} is not in the tenant's approved list")


# ------------------------------------------------------------------ runtime contract


@dataclass(frozen=True)
class MarketContext:
    """Inputs a strategy may read. Built by the runner; strategies never call brokers."""

    now: datetime
    bars: Mapping[str, Sequence[Bar]]  # symbol -> closed bars, oldest first (today's session for intraday)
    reference: Mapping[str, Sequence[Bar]] = field(default_factory=dict)  # e.g. {"SPY": [...]} for regime
    facts: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)  # per-symbol extras (tier, rvol, ...)


@dataclass(frozen=True)
class SignalIntent:
    """What a strategy wants. The risk engine decides whether it may happen."""

    strategy_id: str
    strategy_version: str
    symbol: str
    side: Literal["BUY"]
    entry_limit: float
    stop: float
    target: float | None
    time_exit: str | None  # "HH:MM" ET, or None
    signal_ts: datetime
    inputs: Mapping[str, Any]  # every decision input, for the journal (§2C)
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("entry_limit", "stop"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} not finite")
        if self.stop >= self.entry_limit:
            raise ValueError("long intent needs stop < entry")


@dataclass(frozen=True)
class Skip:
    """A considered-but-rejected candidate, logged as SignalBlocked (shadow) by the runner."""

    symbol: str
    reason: str
    inputs: Mapping[str, Any] = field(default_factory=dict)


@runtime_checkable
class Strategy(Protocol):
    spec: StrategySpec

    def evaluate(self, ctx: MarketContext) -> Sequence[SignalIntent | Skip]:
        """Pure function of ``ctx`` (and the spec). No I/O, no broker calls, no clock reads."""
        ...
