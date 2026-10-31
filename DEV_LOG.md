# DEV_LOG — pios-algo

## 2026-10-31 — Build step 1: event envelope, event store, legacy import
Built by Claude in the planning chat; copied into SDE.

**Done**
- Envelope v1 with the brief's fields and rules; JSON Schema export plus a drift test.
- `EventStore` port + SQLite implementation (per-tenant file, WAL, append-only triggers, idempotent by `event_id`, optimistic concurrency per stream, atomic batches).
- Upcaster/importer for the day-1 JSONL. Real 10/30 file: 64 lines in → 64 events out, re-import adds 0, nothing unmapped.
- ADR-003 merge-ready brick (Will, 10:07): `algo.` event namespace, `algo_` SQL prefix, `algo_schema_migrations`, import-boundary test.
- Checks: 43 tests pass; ruff clean; mypy strict clean on `events`, `tenancy`, `core`.

**Deviations from the brief (reason → consequence)**
1. `requires-python >= 3.10`, not 3.12. The laptop's Linux shell has 3.10 → runs on both; mypy still targets 3.12.
2. Added journal event types (`AccountSnapshot`, `DecisionRecorded`, `ConfigChanged`, `PositionChecked`, `ResultRecorded`, `AnalysisRecorded`, `NoteRecorded`). The brief would have stored most day-1 lines as `DeviationLogged` → day-1 history keeps its meaning; zero lines unmapped.
3. Event type values prefixed `algo.` and tables prefixed `algo_` (ADR-003, decided after the brief) → safe to share a DB with PIOS.
4. Tests use a synthetic fixture (`tests/fixtures/legacy-sample.jsonl`); the real 10/30 file lives in `will-strategies/data/events/` → no tenant trading data in the platform repo (ADR-002 A7).
5. Importer named `scripts/import_legacy.py` (brief: `import_day1.py`) since it takes any legacy file.
6. Legacy `order_instruction` lines import as live `algo.OrderPlaced` without `risk_check_id`; allowed only when `source="claude"` and `payload.imported=true` → day-1 history fits; new orders can't take that path.

**Bug found by real data**
- The 10/30 `opening_range` line has `"fields"` as a string; the symbol lookup assumed an object and crashed. Fixed, regression test added.

**Next (step 2)**
`Strategy` interface + spec loader (`designed_on`, `expected_signals_per_week`, `autonomy_level`); move MOM-01 into `will-strategies`; platform bounds (ADR-002 A6) + account-wide limits (architecture §2A: 6 positions, 35%/symbol, 50%/group, same-symbol block, −5% daily); live refuses to start with any limit unset.
