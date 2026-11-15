# compute (C++)

C++ compute for pios-algo, per ADR-PIOS-ALGO-009 (amended 2026-11-14: best-fit language from day one). Built so far: `indicators/` (`vwap_series`, `atr`, opening-range low/high), exposed to Python as `pios_algo_compute` and called from `pios_algo.core.bars`. Golden tests: `tests/test_native_golden.py`.

## Components

| Folder | Component | Scope |
| --- | --- | --- |
| `backtest/` | Backtest and parameter-sweep engine | Research |
| `scanner/` | Market-wide scanner (PIOS workstation, ADR-PIOS-ALGO-019) | Research and live display |
| `indicators/` | Indicator library, one library for backtests and the live engine | Research and live |
| `montecarlo/` | Monte Carlo risk simulation | Research |
| `options/` | Options pricing and Greeks (QuantLib) | Research only |
| `orderbook/` | Order-book and tick research | Research only, no HFT |

## Rules

- **C++ computes, Python decides.** Native code never owns policy, authorization, broker connectivity, order state, risk decisions or financial truth. A native crash must never leave a position without an exit.
- Python reaches it only through pybind11 or a typed, versioned service contract.
- Deterministic and Decimal-safe wherever money is involved.
- Accuracy tests against golden datasets with known answers, plus cross-checks wherever a reference implementation exists.
- Fuzzing and memory-safety review; reproducible builds on Windows, Linux arm64 and CI from the first commit; versioned artifacts.
- Passes the same conformance suites as every other runtime.

## Build

The Python module builds during `uv pip install -e ".[dev]"` in pios-algo. A plain CMake build from the PIOS repo root builds the library, plus the module if pybind11's CMake files are found:

```bash
bash scripts/task.sh compute build
bash scripts/task.sh compute test   # no C++-level tests yet; parity is checked in pytest
```

Still to add: a sanitizer build option, a fuzz target and C++ unit tests.
