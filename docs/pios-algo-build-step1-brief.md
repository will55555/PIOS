# pios-algo — Build step 1 brief (for Claude Code on the laptop)

> **Status 2026-10-31: BUILT** (step 1 done ~10:12 ET by Claude in the planning chat, not Claude Code; commits pios-algo 2af7a93 / will-strategies e653f77 in `SDE`). Deviations from this brief are listed in `pios-algo/DEV_LOG.md` (Python ≥ 3.10, extra journal event types, `algo.` / `algo_` prefixes per ADR-003, synthetic test fixture, importer named `scripts/import_legacy.py`). Kept as the historical spec; current design: claude/pios-algo-architecture.md v0.6.

Written 2026-10-30 23:25 ET. Architecture §5 step 1. Source of truth: claude/pios-algo-architecture.md v0.5 §1–3, ADR-001 (Accepted), ADR-002 v3 (Accepted). Will scaffolds the repos himself; this brief is the spec.

## Scope (step 1 only)
1. Two repos: `pios-algo` (Terra GitHub org, private) and `will-strategies` (Will's personal GitHub, private). `will-strategies` gets only a README, `specs/` and `strategies/` folders now (strategies move in at step 2).
2. `pios-algo` Python package `pios_algo` (Python 3.12, `pyproject.toml`, pytest, ruff, mypy strict on `core/` and `events/`). Folders now: `core/`, `events/`, `tenancy/`, `adapters/`, `projections/`, `runner/`, `monitor/`, `api/`, `lambdas/`, `infra/terraform/` — empty `__init__.py` except what's below.
3. **Event envelope** (`events/envelope.py`, pydantic v2, frozen):
   - Top: `event_id` (UUID4), `tenant_id` (required, non-empty, `[a-z0-9-]+`), `stream` (`trade|sleeve|system|signal`), `stream_id`, `type` (enum of the core types in architecture §3), `version` (int ≥ 1), `ts` (timezone-aware; reject naive), `payload` (dict).
   - `meta`: `source` (`engine|lambda|claude|will`), `strategy`, `strategy_version`, `param_hash`, `sleeve`, `mode` (`live|paper|shadow|backtest`), `autonomy_level` (`L0|L1|L2|L3`), `rule_ref`, `risk_check_id` (UUID or null), `host` (`spot|ondemand|lambda|claude|local`), `broker`, `account` (ADR-001 §3).
   - Validation rules: `OrderPlaced` with `mode=live|paper` requires `risk_check_id` (architecture §2C); `AutonomyLevelChanged`, `FreezeSet`, `FreezeLifted`, `KillSwitchReset` require `source=will`; no NaN/inf anywhere in `payload` (§2C indicator validity).
   - JSON Schema exported to `schemas/event-envelope.v1.json` (the cross-language contract, ADR-001 §5); a test fails if the export drifts from the model.
4. **Event store port** (`events/store.py`): `append(events, expected_version=None)`, `read_stream(tenant_id, stream_id)`, `read_all(tenant_id, since=None)`. Append-only: no update/delete methods. Optimistic concurrency per stream. Idempotent on `event_id` (re-append of the same id = no-op; same id with different content = error).
5. **SQLite implementation** (`events/sqlite_store.py`): one DB file per tenant at `data/tenants/<tenant_id>/events.db`; WAL mode; table with `global_seq` autoincrement, `stream_id`, `stream_version`, unique `(stream_id, stream_version)` and unique `event_id`; JSON stored as text. A tenant can never read another tenant's file (path built from validated `tenant_id` only).
6. **Upcaster + importer** (`events/upcast.py`, `scripts/import_day1.py`): read `claude/mom01-events/2026-10-30.jsonl` (download from the Project), map legacy `type` values → envelope types, add `tenant_id="will"`, `source` from content (`user_*` → `will`, else `claude`), naive `ts` → `America/New_York`, keep the original line under `payload.legacy`. Legacy types with no mapping → `DeviationLogged` / `system` stream with `payload.legacy_type`. Mapping table lives in code and the README.
   - Suggested mapping: `signal`→SignalDetected; `signal_blocked`,`signal_not_taken`→SignalBlocked; `order_instruction`→OrderPlaced (mode live, `risk_check_id` null allowed only for `meta.source=claude` imports flagged `payload.imported=true`); `fill`→OrderFilled; `order_revoked`→OrderRevoked; `stop_hit`→StopHit; `deviation`→DeviationLogged; `account`,`user_decision`,`rule_change`,`config_change`,`setup`,`context`,`universe`,… → system-stream events.
7. **Tests (pytest):** envelope validation (each rule above, good + bad); store append/read/idempotency/concurrency conflict/tenant isolation; importer round-trip — the file must import with **every line accounted for** (count in = count out) and a second import adds 0 events.

## Not in step 1
Strategy interface, bounds, account limits (step 2); Webull adapter + keys (step 3); Terraform beyond an empty `infra/terraform/README.md`; any network calls.

## Rules carried from the Project
- No keys anywhere in either repo, chat or synced folders; `.gitignore` covers `data/`, `.env*`, `*.db`.
- `pios-algo` holds no strategy logic (ADR-002 A1).
- Log deviations from this brief in the repo's `DEV_LOG.md` (reason + consequence).
- Commit trailer per Will's hub conventions.

## Done when
Tests green, the importer reports N lines in = N events out for the 10/30 file, the schema JSON is committed, and Will pastes the test summary + import counts back into the Algo Trading chat so the state doc can be updated.
