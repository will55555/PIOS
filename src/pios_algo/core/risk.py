"""Risk: platform bounds (ADR-002 A6), account-wide limits (architecture §2A, E13), sizing, live readiness.

Order of checks for every entry: per-trade sizing → sleeve cash → account-wide limits.
The AI can't change any of these values; only the tenant edits their config (§1 decision chain).
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from pios_algo.core.strategy_api import (
    ApprovedVersion,
    SignalIntent,
    StrategySpec,
    UnapprovedSpec,
    check_approved,
)

# ------------------------------------------------------------------ platform bounds (A6)


class PlatformBounds(BaseModel):
    """Hard limits no tenant can exceed. Values accepted by Will 2026-10-30 23:20 (ADR-002 v3 A6)."""

    model_config = ConfigDict(frozen=True)

    max_risk_per_trade_pct: float = 10.0
    kill_switch_required_above_risk_pct: float = 5.0
    max_kill_switch_drawdown_pct: float = 50.0
    monthly_loss_cap_required: bool = True
    max_monthly_loss_cap_pct: float = 50.0
    # Always on, not configurable: fail closed, settled cash only, long only (no margin/shorting/options).


A6_BOUNDS = PlatformBounds()


def bound_violations(spec: StrategySpec, bounds: PlatformBounds = A6_BOUNDS) -> list[str]:
    r = spec.risk
    out: list[str] = []
    top = max(r.risk_per_trade_pct, r.a_plus_risk_pct or 0.0)
    if top > bounds.max_risk_per_trade_pct:
        out.append(f"{spec.key}: risk per trade {top}% > {bounds.max_risk_per_trade_pct}%")
    if top > bounds.kill_switch_required_above_risk_pct and r.kill_switch_pct is None:
        out.append(f"{spec.key}: risk {top}% > {bounds.kill_switch_required_above_risk_pct}% needs a kill switch")
    if r.kill_switch_pct is not None and r.kill_switch_pct > bounds.max_kill_switch_drawdown_pct:
        limit = bounds.max_kill_switch_drawdown_pct
        out.append(f"{spec.key}: kill switch at -{r.kill_switch_pct}% looser than -{limit}%")
    if bounds.monthly_loss_cap_required and r.monthly_loss_cap_pct is None:
        out.append(f"{spec.key}: monthly loss cap required")
    if r.monthly_loss_cap_pct is not None and r.monthly_loss_cap_pct > bounds.max_monthly_loss_cap_pct:
        out.append(f"{spec.key}: monthly cap {r.monthly_loss_cap_pct}% looser than {bounds.max_monthly_loss_cap_pct}%")
    return out


# ------------------------------------------------------------------ account-wide limits (§2A)


class SmallAccountTier(BaseModel):
    """Looser exposure caps while equity is small (Will 2026-10-31): one position per sleeve is
    otherwise impossible at ~$150 equity. Reverts to the normal caps once equity reaches ``equity_below``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    equity_below: float = Field(gt=0)
    max_symbol_exposure_pct: float = Field(gt=0, le=100)
    max_group_exposure_pct: float = Field(gt=0, le=100)


class AccountLimits(BaseModel):
    """Tenant-set account-wide limits. Every field must be set before live starts (E13).
    ``small_account`` is optional and only loosens the two exposure caps below its equity threshold."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_concurrent_positions: int | None = Field(default=None, ge=1)
    max_positions_per_strategy: dict[str, int] | None = None
    max_symbol_exposure_pct: float | None = Field(default=None, gt=0, le=100)
    max_group_exposure_pct: float | None = Field(default=None, gt=0, le=100)
    block_same_symbol_across_strategies: bool | None = None
    daily_loss_stop_pct: float | None = Field(default=None, gt=0, le=100)
    small_account: SmallAccountTier | None = None

    def unset(self) -> list[str]:
        return [name for name, value in self if value is None and name != "small_account"]

    def exposure_caps(self, equity: float) -> tuple[float, float]:
        """(symbol %, group %) in force at this equity."""
        assert self.max_symbol_exposure_pct is not None and self.max_group_exposure_pct is not None
        tier = self.small_account
        if tier is not None and equity < tier.equity_below:
            return tier.max_symbol_exposure_pct, tier.max_group_exposure_pct
        return self.max_symbol_exposure_pct, self.max_group_exposure_pct


@dataclass(frozen=True)
class Holding:
    """An open position OR a pending (unfilled) buy, valued at market / limit × qty."""

    symbol: str
    strategy_id: str
    group: str
    value: float
    pending: bool = False


@dataclass(frozen=True)
class AccountState:
    equity: float
    start_of_day_equity: float
    sleeve_settled_cash: Mapping[str, float]
    holdings: Sequence[Holding] = ()
    frozen: bool = False
    kill_switched_sleeves: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RiskDecision:
    passed: bool
    reason: str | None = None  # "account_limit:<which>" / "sleeve:<which>" / "freeze"
    qty: float = 0.0
    notional: float = 0.0
    risk_check_id: uuid.UUID | None = None
    details: Mapping[str, float] = field(default_factory=dict)


def group_of(symbol: str, asset_class: str, sectors: Mapping[str, str]) -> str:
    """All crypto = one group (E13); stocks by sector map, unknown sector = its own symbol (conservative)."""
    if asset_class == "crypto":
        return "crypto"
    return sectors.get(symbol, f"symbol:{symbol}")


_CAP_REASON = {
    "risk": "sleeve:risk",
    "cash": "sleeve:cash",
    "symbol_exposure": "account_limit:symbol_exposure",
    "group_exposure": "account_limit:group_exposure",
}


def _floor(x: float, decimals: int) -> float:
    f = float(10**decimals)
    return math.floor(x * f) / f


def check_entry(
    intent: SignalIntent,
    spec: StrategySpec,
    state: AccountState,
    limits: AccountLimits,
    sectors: Mapping[str, str],
    *,
    a_plus: bool = False,
    qty_decimals: int = 4,
) -> RiskDecision:
    """Size the trade and check every account-wide limit. Returns qty clipped to what the limits allow;
    blocks if nothing is allowed. Raises if any limit is unset (live must not start that way)."""
    missing = limits.unset()
    if missing:
        raise ValueError(f"account limits unset: {missing}")
    assert limits.max_concurrent_positions is not None and limits.max_symbol_exposure_pct is not None
    assert limits.max_group_exposure_pct is not None and limits.daily_loss_stop_pct is not None
    assert limits.max_positions_per_strategy is not None

    def block(reason: str, **d: float) -> RiskDecision:
        return RiskDecision(False, reason, details=d)

    if state.frozen:
        return block("freeze")
    if spec.sleeve in state.kill_switched_sleeves:
        return block("sleeve:kill_switch")
    if state.equity <= state.start_of_day_equity * (1 - limits.daily_loss_stop_pct / 100):
        return block("account_limit:daily_loss_stop", equity=state.equity, sod=state.start_of_day_equity)

    held_symbols = {h.symbol for h in state.holdings}
    if limits.block_same_symbol_across_strategies and intent.symbol in held_symbols:
        return block("account_limit:same_symbol")
    if len(held_symbols) >= limits.max_concurrent_positions:
        return block("account_limit:max_positions", open=len(held_symbols))
    per_strat = limits.max_positions_per_strategy.get(spec.id)
    mine = {h.symbol for h in state.holdings if h.strategy_id == spec.id}
    if per_strat is not None and len(mine) >= per_strat:
        return block("account_limit:max_positions_strategy", open=len(mine))
    if len(mine) >= spec.risk.max_concurrent_positions:
        return block("sleeve:max_positions", open=len(mine))

    cash = state.sleeve_settled_cash.get(spec.sleeve, 0.0)
    if cash <= 0:
        return block("sleeve:no_settled_cash")
    risk_pct = spec.risk.a_plus_risk_pct if (a_plus and spec.risk.a_plus_risk_pct) else spec.risk.risk_per_trade_pct
    per_share_risk = intent.entry_limit - intent.stop
    group = group_of(intent.symbol, spec.asset_class, sectors)
    sym_pct, grp_pct = limits.exposure_caps(state.equity)
    sym_room = state.equity * sym_pct / 100 - sum(
        h.value for h in state.holdings if h.symbol == intent.symbol
    )
    grp_room = state.equity * grp_pct / 100 - sum(
        h.value for h in state.holdings if h.group == group
    )
    caps = {
        "risk": cash * risk_pct / 100 / per_share_risk * intent.entry_limit,
        "cash": cash,
        "symbol_exposure": sym_room,
        "group_exposure": grp_room,
    }
    binding = min(caps, key=lambda k: caps[k])
    qty = _floor(max(caps[binding], 0.0) / intent.entry_limit, qty_decimals)
    if qty <= 0:
        return block(_CAP_REASON[binding], **caps)
    return RiskDecision(
        True,
        None,
        qty=qty,
        notional=round(qty * intent.entry_limit, 2),
        risk_check_id=uuid.uuid4(),
        details={**caps, f"binding:{binding}": 1.0},
    )


# ------------------------------------------------------------------ live readiness


class LiveNotReady(RuntimeError):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("live start refused:\n- " + "\n- ".join(problems))
        self.problems = problems


def live_readiness_problems(
    specs: Sequence[StrategySpec],
    limits: AccountLimits,
    approved: Sequence[ApprovedVersion],
    bounds: PlatformBounds = A6_BOUNDS,
) -> list[str]:
    problems = [f"account limit unset: {name}" for name in limits.unset()]
    for spec in specs:
        problems += bound_violations(spec, bounds)
        try:
            check_approved(spec, approved)
        except UnapprovedSpec as e:
            problems.append(str(e))
        if spec.autonomy_level == "L0":
            problems.append(f"{spec.key}: autonomy L0 is paper only")
        if spec.expected_signals_per_week is None:
            problems.append(f"{spec.key}: expected_signals_per_week not set (signal-drift monitor needs it, §2C)")
    return problems


def assert_live_ready(
    specs: Sequence[StrategySpec],
    limits: AccountLimits,
    approved: Sequence[ApprovedVersion],
    bounds: PlatformBounds = A6_BOUNDS,
) -> None:
    problems = live_readiness_problems(specs, limits, approved, bounds)
    if problems:
        raise LiveNotReady(problems)
