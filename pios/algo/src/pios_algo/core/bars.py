"""Generic, tenant-neutral market-data helpers (split out of algo_lib.py v1.1).

Every helper returns finite numbers or raises ``InvalidIndicator`` — never NaN/None
in a decision input (architecture §2C indicator validity).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


class InvalidIndicator(ValueError):
    """A decision input could not be computed as a finite number."""


@dataclass(frozen=True)
class Bar:
    """One OHLCV bar. ``t`` = timezone-aware START of the bar; ``span_min`` = bar length."""

    t: datetime
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    v: float = 0.0
    span_min: int = 5

    def __post_init__(self) -> None:
        if self.t.tzinfo is None:
            raise ValueError("Bar.t must be timezone-aware")
        for name in ("o", "h", "l", "c", "v"):
            if not math.isfinite(getattr(self, name)):
                raise InvalidIndicator(f"bar {self.t} has non-finite {name}")

    @property
    def end(self) -> datetime:
        return self.t + timedelta(minutes=self.span_min)


def _finite(x: float, what: str) -> float:
    if not math.isfinite(x):
        raise InvalidIndicator(f"{what} is not finite")
    return x


def rth(bars: Sequence[Bar]) -> list[Bar]:
    """Regular-hours bars only (09:30–16:00 ET)."""
    return [b for b in bars if RTH_OPEN <= b.t.astimezone(ET).time() < RTH_CLOSE]


def closed_only(bars: Sequence[Bar], now: datetime) -> list[Bar]:
    """Drop any bar that has not closed yet."""
    return [b for b in bars if b.end <= now]


def vwap_series(bars: Sequence[Bar]) -> list[float]:
    """Cumulative VWAP (typical price) over ``bars``. Zero-volume prefix falls back to close."""
    pv = vol = 0.0
    out: list[float] = []
    for b in bars:
        tp = (b.h + b.l + b.c) / 3
        pv += tp * b.v
        vol += b.v
        out.append(_finite(pv / vol if vol else b.c, "vwap"))
    return out


def atr(bars: Sequence[Bar], n: int = 14) -> float:
    """Simple ATR over the last ``n`` true ranges. Raises if fewer than 2 bars."""
    if len(bars) < 2:
        raise InvalidIndicator("atr needs at least 2 bars")
    trs = []
    for prev, b in zip(bars, bars[1:], strict=False):
        trs.append(max(b.h - b.l, abs(b.h - prev.c), abs(b.l - prev.c)))
    trs = trs[-n:]
    return _finite(sum(trs) / len(trs), "atr")


@dataclass(frozen=True)
class OpeningRange:
    low: float
    high: float
    mid: float
    width_pct: float
    vwap_at_end: float
    end: time


def opening_range(today_rth: Sequence[Bar], minutes: int) -> OpeningRange | None:
    """Opening range over the first ``minutes`` of RTH. None if the range is not complete yet."""
    if not today_rth:
        return None
    span = today_rth[0].span_min
    need = minutes // span
    end_t = (datetime.combine(today_rth[0].t.date(), RTH_OPEN) + timedelta(minutes=minutes)).time()
    orb = [b for b in today_rth if b.t.astimezone(ET).time() < end_t]
    if len(orb) < need:
        return None
    lo, hi = min(b.l for b in orb), max(b.h for b in orb)
    if lo <= 0:
        raise InvalidIndicator("opening range low <= 0")
    return OpeningRange(
        low=lo,
        high=hi,
        mid=round((lo + hi) / 2, 4),
        width_pct=round((hi - lo) / ((hi + lo) / 2) * 100, 3),
        vwap_at_end=round(vwap_series(orb)[-1], 4),
        end=end_t,
    )


def r_multiple(entry: float, stop: float, exit_px: float, cost_pct: float = 0.0) -> float:
    """R after a round-trip cost given as % of entry price."""
    risk = entry - stop
    if risk <= 0:
        raise InvalidIndicator("risk must be positive (entry > stop)")
    return round((exit_px - entry - entry * cost_pct / 100) / risk, 3)
