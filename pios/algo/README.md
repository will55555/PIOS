# pios-algo

Terra's multi-tenant, bring-your-own-strategy algo trading platform — the PIOS algo layer. Will is tenant #1.

- **Platform only.** Tenant strategies live in their own repos (Will's: `will-strategies`) and load as config (ADR-002 A1).
- **Merge-ready brick.** Can be merged into the PIOS repo later; the engine and watchdog always stay separate processes (docs/adr/ADR-003).
- **Event-sourced.** Every signal, order, fill and decision is an append-only event; positions and ledgers are projections.

Design docs: `docs/pios-algo-architecture.md` v0.6, `docs/pios-algo-build-step1-brief.md`, `docs/adr/`. ADR-001 and ADR-002 v3 (both Accepted) are in the Algo Trading Project. State and planning notes are private: `will-strategies/docs/`.

## Status — build step 1 (2026-10-31)
| Piece | Where |
| --- | --- |
| Event envelope v1 (`tenant_id`, `risk_check_id`, `param_hash`, `autonomy_level`, `broker`, `account`, `correlation_id`, `causation_id`) | `src/pios_algo/events/envelope.py` |
| JSON Schema (cross-language contract) | `schemas/event-envelope.v1.json` |
| `EventStore` port (append-only, idempotent, optimistic concurrency) | `src/pios_algo/events/store.py` |
| SQLite store, one file per tenant, `algo_` tables, append-only triggers | `src/pios_algo/events/sqlite_store.py` |
| Legacy JSONL upcaster + importer | `src/pios_algo/events/upcast.py`, `scripts/import_legacy.py` |

Envelope rules enforced in code: timezone-aware `ts`; no NaN/inf anywhere in `payload`; `algo.OrderPlaced` in live/paper needs `meta.risk_check_id`; `algo.AutonomyLevelChanged`, `algo.FreezeSet`, `algo.FreezeLifted`, `algo.KillSwitchReset` only from `source="will"`. The store refuses any event version it has no upcast path for, on read and on append (PIOS ADR-013).

## Status — build step 2 (2026-10-31)
| Piece | Where |
| --- | --- |
| `Strategy` protocol, `StrategySpec` (`designed_on`, `expected_signals_per_week`, `autonomy_level`, risk rules), `param_hash`, approval check | `src/pios_algo/core/strategy_api.py` |
| Generic bars/indicators (VWAP, ATR, opening range, R) — finite or raise | `src/pios_algo/core/bars.py` |
| Platform bounds A6, account-wide limits §2A (sizing clipped to limits, `risk_check_id`), live readiness gate | `src/pios_algo/core/risk.py` |
| Tenant config (limits, approved versions, sector map) | `src/pios_algo/tenancy/config.py` |

Live refuses to start (`LiveNotReady`) if any account limit is unset, any spec breaks A6, any spec isn't approved at its exact `param_hash`, a spec is L0, or `expected_signals_per_week` is missing.

Next: step 3 — Webull adapter against paperTrade keys (per-tenant KMS/SSM).

## New machine
One command installs or updates what pios-algo needs, then builds it:

| OS | Command |
| --- | --- |
| Windows (PowerShell) | `powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1` |
| Linux / macOS | `bash scripts/bootstrap.sh` |

It installs or updates uv and the C++ compiler (Visual Studio Build Tools on Windows, build-essential or the
Xcode tools elsewhere; this may ask for admin or sudo). It installs Python from `.python-version`, creates
`.venv`, and runs `uv pip install -e ".[dev]"`, which compiles the C++ module. The build downloads CMake and
Ninja itself. Add `-Upgrade` / `--upgrade` to move packages to the newest versions `pyproject.toml` allows;
`-Check` / `--check` only reports what is missing.

**VS Code:** open the `pios-algo` folder (it is also a root in `terra-workspace.code-workspace`), accept the
recommended extensions, and allow automatic tasks once. The setup check then runs every time the folder opens;
**Tasks: Run Task → pios-algo: bootstrap** does the full setup.

## Run
Installing now compiles the C++ indicator library in `compute/` (scikit-build-core + pybind11), so it needs a C++20 compiler: MSVC 2022, GCC 11+ or Clang 15+. If the module isn't built, indicators raise `InvalidIndicator` (no entries); `Bar`, risk and exits still work.
```bash
uv venv --python 3.15 --seed .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"                            # engine runs on 3.15, Lambdas on 3.14 (the floor)
pytest && ruff check . && mypy
python scripts/export_schema.py                    # after any envelope change
python scripts/import_legacy.py ../will-strategies/data/events/2026-10-30.jsonl --tenant will --root data
```
Windows PowerShell 5.1 has no `&&`: run `pytest; ruff check .; mypy` instead.

## Legacy import mapping
| Legacy `type` | Event type | Stream |
| --- | --- | --- |
| signal | algo.SignalDetected | signal |
| signal_blocked, signal_not_taken | algo.SignalBlocked | signal |
| order_instruction | algo.OrderPlaced | trade |
| fill | algo.OrderFilled | trade |
| order_revoked | algo.OrderRevoked | trade |
| stop_hit | algo.StopHit | trade |
| position_check | algo.PositionChecked | trade |
| eod_comparison | algo.ResultRecorded | trade |
| shadow_result | algo.ResultRecorded | signal |
| day_summary | algo.ResultRecorded | system |
| deviation | algo.DeviationLogged | system |
| account | algo.AccountSnapshot | sleeve |
| user_decision, rule_change, user_correction | algo.DecisionRecorded | system |
| config_change, setup | algo.ConfigChanged | system |
| analysis, backtest, finding, review | algo.AnalysisRecorded | system |
| design, build, bug_fix, repair, tokens, run, user, user_action, context, universe, opening_range | algo.NoteRecorded | system |
| anything else | algo.DeviationLogged (`payload.legacy_type` set) | system |

Every imported event keeps the original line under `payload.legacy`, has `payload.imported = true`, and a deterministic id (re-import adds nothing). Naive timestamps are read as America/New_York; `user*` lines get `source = "will"`.

## Never in this repo
Broker keys, `.env`, event databases, tenant strategies or tenant trading data.
