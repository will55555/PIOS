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

try:
    import pios_algo_compute as _native  # C++ indicator library (ADR-PIOS-ALGO-009)

    _NATIVE_ERROR: ImportError | None = None
except ImportError as exc:  # not built: indicators fail closed; Bar, risk and exits still work
    _NATIVE_ERROR = exc

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


def _require_native() -> None:
    if _NATIVE_ERROR is not None:
        raise InvalidIndicator("C++ indicator library (pios_algo_compute) is not built") from _NATIVE_ERROR


def rth(bars: Sequence[Bar]) -> list[Bar]:
    """Regular-hours bars only (09:30–16:00 ET)."""
    return [b for b in bars if RTH_OPEN <= b.t.astimezone(ET).time() < RTH_CLOSE]


def closed_only(bars: Sequence[Bar], now: datetime) -> list[Bar]:
    """Drop any bar that has not closed yet."""
    return [b for b in bars if b.end <= now]


def vwap_series(bars: Sequence[Bar]) -> list[float]:
    """Cumulative VWAP (typical price) over ``bars``. Zero-volume prefix falls back to close. Computed in C++."""
    _require_native()
    out = _native.vwap_series([b.h for b in bars], [b.l for b in bars], [b.c for b in bars], [b.v for b in bars])
    return [_finite(x, "vwap") for x in out]


def atr(bars: Sequence[Bar], n: int = 14) -> float:
    """Simple ATR over the last ``n`` true ranges. Raises if fewer than 2 bars. Computed in C++."""
    _require_native()
    if len(bars) < 2:
        raise InvalidIndicator("atr needs at least 2 bars")
    n_tr = len(bars) - 1
    start = slice(-n, None).indices(n_tr)[0]  # the same window as trs[-n:]
    if start >= n_tr:
        raise InvalidIndicator("atr window is empty")
    return _finite(_native.atr([b.h for b in bars], [b.l for b in bars], [b.c for b in bars], start), "atr")


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
    _require_native()
    lo, hi = _native.low_high([b.l for b in orb], [b.h for b in orb])
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
