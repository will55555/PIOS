"""Golden cross-check: the C++ indicators must match the pre-port Python code exactly
(ADR-PIOS-ALGO-009: accuracy tests against a reference implementation)."""

from __future__ import annotations

import random
from collections.abc import Sequence
from datetime import datetime, timedelta

import pytest

from pios_algo.core import bars as bars_mod
from pios_algo.core.bars import ET, Bar, InvalidIndicator, atr, opening_range, rth, vwap_series

# ---------------------------------------------------------------- reference (pre-port code, unchanged)


def ref_vwap(bars: Sequence[Bar]) -> list[float]:
    pv = vol = 0.0
    out: list[float] = []
    for b in bars:
        tp = (b.h + b.l + b.c) / 3
        pv += tp * b.v
        vol += b.v
        out.append(pv / vol if vol else b.c)
    return out


def ref_atr(bars: Sequence[Bar], n: int = 14) -> float:
    trs = [max(b.h - b.l, abs(b.h - p.c), abs(b.l - p.c)) for p, b in zip(bars, bars[1:], strict=False)]
    trs = trs[-n:]
    return sum(trs) / len(trs)


# ---------------------------------------------------------------- inputs

T0 = datetime(2026, 11, 2, 9, 30, tzinfo=ET)
SEEDS = range(50)


def make_bars(seed: int, count: int, as_int: bool = False) -> list[Bar]:
    rng = random.Random(seed)
    px = 100.0
    out: list[Bar] = []
    for i in range(count):
        o = px
        c = o * (1 + rng.uniform(-0.01, 0.01))
        h = max(o, c) * (1 + rng.uniform(0, 0.005))
        lo = min(o, c) * (1 - rng.uniform(0, 0.005))
        v = 0.0 if (seed % 2 and i < 2) else rng.uniform(0, 1e6)
        if as_int:
            o, h, lo, c, v = (float(round(x)) for x in (o, h, lo, c, v))
        out.append(Bar(T0 + timedelta(minutes=5 * i), o, h, lo, c, v))
        px = c
    return out


# ---------------------------------------------------------------- checks


@pytest.mark.parametrize("seed", SEEDS)
def test_vwap_matches_reference(seed: int) -> None:
    b = make_bars(seed, 2 + seed * 3)
    assert vwap_series(b) == ref_vwap(b)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("n", [0, 1, 5, 14, 500])
def test_atr_matches_reference(seed: int, n: int) -> None:
    b = make_bars(seed, 2 + seed * 3)
    assert atr(b, n) == ref_atr(b, n)


def test_whole_number_prices_match_reference() -> None:
    b = make_bars(7, 40, as_int=True)
    assert vwap_series(b) == ref_vwap(b)
    assert atr(b) == ref_atr(b)


def test_opening_range_low_high_matches_python() -> None:
    b = make_bars(3, 12)
    orx = opening_range(b, 60)
    assert orx is not None
    assert (orx.low, orx.high) == (min(x.l for x in b), max(x.h for x in b))


def test_atr_empty_window_fails_closed() -> None:
    with pytest.raises(InvalidIndicator):
        atr(make_bars(1, 3), n=-5)


def test_missing_native_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bars_mod, "_NATIVE_ERROR", ImportError("simulated missing build"))
    b = make_bars(2, 5)
    with pytest.raises(InvalidIndicator):
        atr(b)
    with pytest.raises(InvalidIndicator):
        vwap_series(b)
    # Bar and the pure-Python helpers keep working without the C++ build.
    assert Bar(T0, 1.0, 1.0, 1.0, 1.0)
    assert rth(b) == b
