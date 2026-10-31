from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

from pios_algo.core.bars import ET, Bar, InvalidIndicator, atr, opening_range, r_multiple, rth, vwap_series
from pios_algo.core.risk import (
    A6_BOUNDS,
    AccountLimits,
    AccountState,
    Holding,
    LiveNotReady,
    assert_live_ready,
    bound_violations,
    check_entry,
    live_readiness_problems,
)
from pios_algo.core.strategy_api import (
    ApprovedVersion,
    SignalIntent,
    StrategySpec,
    UnapprovedSpec,
    check_approved,
    load_spec,
)
from pios_algo.tenancy.config import TenantConfig

T0 = datetime(2026, 11, 2, 9, 30, tzinfo=ET)

E13 = AccountLimits(
    max_concurrent_positions=6,
    max_positions_per_strategy={"MOM-01": 3, "VOL-01": 3},
    max_symbol_exposure_pct=35,
    max_group_exposure_pct=50,
    block_same_symbol_across_strategies=True,
    daily_loss_stop_pct=5,
)


def bars(prices: list[tuple[float, float, float, float]], start: datetime = T0, v: float = 1000) -> list[Bar]:
    return [Bar(start + timedelta(minutes=5 * i), o, h, low, c, v) for i, (o, h, low, c) in enumerate(prices)]


def spec(**risk) -> StrategySpec:
    base = dict(risk_per_trade_pct=1.0, monthly_loss_cap_pct=10.0, max_concurrent_positions=3)
    base.update(risk)
    return StrategySpec(
        id="MOM-01",
        version="1.1",
        name="test",
        asset_class="us_stock",
        sleeve="core",
        autonomy_level="L2",
        designed_on={"end": "2026-10-30"},
        expected_signals_per_week=2.0,
        risk=base,
        params={"x": 1},
    )


def intent(symbol: str = "AAPL", entry: float = 348.94, stop: float = 346.45) -> SignalIntent:
    return SignalIntent("MOM-01", "1.1", symbol, "BUY", entry, stop, None, "15:50", T0, {})


# ---------------------------------------------------------------- bars


def test_vwap_and_atr():
    b = bars([(10, 11, 9, 10), (10, 12, 10, 11)])
    assert vwap_series(b) == [10.0, pytest.approx((10 + 11) / 2)]
    assert atr(b) == 2.0
    with pytest.raises(InvalidIndicator):
        atr(b[:1])


def test_bar_rejects_nan_and_naive():
    with pytest.raises(InvalidIndicator):
        Bar(T0, 1, float("nan"), 1, 1)
    with pytest.raises(ValueError):
        Bar(datetime(2026, 11, 2, 9, 30), 1, 1, 1, 1)


def test_opening_range_needs_full_window():
    b = bars([(100, 101, 99, 100)] * 11)
    assert opening_range(b, 60) is None
    orx = opening_range(bars([(100, 101, 99, 100)] * 12), 60)
    assert orx is not None and (orx.low, orx.high, orx.mid) == (99, 101, 100.0)


def test_rth_filter_and_r():
    pre = Bar(T0 - timedelta(minutes=30), 1, 1, 1, 1)
    assert rth([pre] + bars([(1, 1, 1, 1)])) != [pre]
    assert r_multiple(100, 98, 104) == 2.0


# ---------------------------------------------------------------- spec + approval


def test_param_hash_changes_with_params_not_notes():
    a = spec()
    b = a.model_copy(update={"name": "renamed", "source_ref": "x"})
    c = a.model_copy(update={"params": {"x": 2}})
    assert a.param_hash == b.param_hash != c.param_hash


def test_approval_check():
    s = spec()
    check_approved(s, [ApprovedVersion("MOM-01", "1.1", s.param_hash)])
    with pytest.raises(UnapprovedSpec):
        check_approved(s, [ApprovedVersion("MOM-01", "1.1", "0" * 64)])
    with pytest.raises(UnapprovedSpec):
        check_approved(s, [])


def test_load_spec_roundtrip(tmp_path):
    p = tmp_path / "s.json"
    p.write_text(spec().model_dump_json())
    assert load_spec(p).param_hash == spec().param_hash


def test_spec_rejects_nan_param():
    with pytest.raises(ValueError):
        spec().model_validate({**json.loads(spec().model_dump_json()), "params": {"x": float("nan")}})


# ---------------------------------------------------------------- A6 bounds


def test_bounds_mom01_and_vol01_shapes():
    assert bound_violations(spec()) == []
    vol = spec(risk_per_trade_pct=5, a_plus_risk_pct=10, kill_switch_pct=50, monthly_loss_cap_pct=50)
    assert bound_violations(vol) == []


@pytest.mark.parametrize(
    "risk,needle",
    [
        ({"risk_per_trade_pct": 11}, "risk per trade"),
        ({"risk_per_trade_pct": 6}, "needs a kill switch"),
        ({"risk_per_trade_pct": 6, "kill_switch_pct": 60}, "looser than -50"),
        ({"monthly_loss_cap_pct": None}, "monthly loss cap required"),
        ({"monthly_loss_cap_pct": 60}, "monthly cap"),
    ],
)
def test_bound_violations(risk, needle):
    assert any(needle in v for v in bound_violations(spec(**risk), A6_BOUNDS))


# ---------------------------------------------------------------- account limits


def state(**kw) -> AccountState:
    base = dict(equity=150.0, start_of_day_equity=150.0, sleeve_settled_cash={"core": 100.0})
    base.update(kw)
    return AccountState(**base)


def test_unset_limit_refuses():
    with pytest.raises(ValueError, match="unset"):
        check_entry(intent(), spec(), state(), AccountLimits(), {})


def test_symbol_exposure_clips_size():
    d = check_entry(intent(), spec(), state(), E13, {"AAPL": "tech"})
    assert d.passed and d.risk_check_id is not None
    assert d.notional <= 150 * 0.35 + 0.01
    assert "binding:symbol_exposure" in d.details


def test_same_symbol_blocked_across_strategies():
    h = Holding("AAPL", "VOL-01", "tech", 20.0)
    d = check_entry(intent(), spec(), state(holdings=[h]), E13, {"AAPL": "tech"})
    assert (d.passed, d.reason) == (False, "account_limit:same_symbol")


def test_group_exposure_blocks_when_full():
    hs = [Holding("MSFT", "VOL-01", "tech", 40.0), Holding("NVDA", "VOL-01", "tech", 35.0)]
    d = check_entry(intent(), spec(), state(holdings=hs), E13, {"AAPL": "tech", "MSFT": "tech", "NVDA": "tech"})
    assert (d.passed, d.reason) == (False, "account_limit:group_exposure")


def test_max_positions_and_per_strategy():
    six = [Holding(f"S{i}", "VOL-01", f"g{i}", 1.0) for i in range(6)]
    assert check_entry(intent(), spec(), state(holdings=six), E13, {}).reason == "account_limit:max_positions"
    three = [Holding(f"S{i}", "MOM-01", f"g{i}", 1.0) for i in range(3)]
    d = check_entry(intent(), spec(), state(holdings=three), E13, {})
    assert d.reason == "account_limit:max_positions_strategy"


def test_daily_stop_freeze_kill_cash():
    assert check_entry(intent(), spec(), state(equity=142.0), E13, {}).reason == "account_limit:daily_loss_stop"
    assert check_entry(intent(), spec(), state(frozen=True), E13, {}).reason == "freeze"
    assert check_entry(intent(), spec(), state(kill_switched_sleeves=frozenset({"core"})), E13, {}).reason == (
        "sleeve:kill_switch"
    )
    assert check_entry(intent(), spec(), state(sleeve_settled_cash={}), E13, {}).reason == "sleeve:no_settled_cash"


def test_crypto_is_one_group():
    cs = spec().model_copy(update={"asset_class": "crypto", "sleeve": "vol"})
    hs = [Holding("BTCUSD", "VOL-01", "crypto", 75.0)]
    d = check_entry(intent("OPUSD", 0.122, 0.116), cs, state(holdings=hs, sleeve_settled_cash={"vol": 25.0}), E13, {})
    assert (d.passed, d.reason) == (False, "account_limit:group_exposure")


# ---------------------------------------------------------------- live readiness


def test_live_refuses_with_unset_limits_and_unapproved():
    probs = live_readiness_problems([spec()], AccountLimits(), [])
    assert any("unset" in p for p in probs) and any("approved" in p for p in probs)
    with pytest.raises(LiveNotReady):
        assert_live_ready([spec()], AccountLimits(), [])


def test_live_ready_when_everything_set():
    s = spec()
    assert_live_ready([s], E13, [ApprovedVersion(s.id, s.version, s.param_hash)])


def test_live_refuses_l0_and_missing_signal_rate():
    s = spec().model_copy(update={"autonomy_level": "L0", "expected_signals_per_week": None})
    probs = live_readiness_problems([s], E13, [ApprovedVersion(s.id, s.version, s.param_hash)])
    assert any("L0" in p for p in probs) and any("expected_signals_per_week" in p for p in probs)


def test_tenant_config_parses():
    cfg = TenantConfig(tenant_id="will", account_limits=E13)
    assert cfg.account_limits.unset() == []
