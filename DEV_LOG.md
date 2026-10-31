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

## 2026-10-31 — Build step 2: strategy interface, bounds, account-wide limits
**Done**
- `core/strategy_api.py`: `Strategy` protocol (pure `evaluate(MarketContext) -> [SignalIntent | Skip]`), `StrategySpec` with `designed_on`, `expected_signals_per_week`, `autonomy_level`, `RiskRules`; `param_hash` = SHA-256 of every behaviour-changing field; `check_approved` refuses any spec not approved at its exact hash.
- `core/bars.py`: generic helpers split from algo_lib v1.1 (VWAP, ATR, opening range, R, RTH filter); NaN/inf → `InvalidIndicator`.
- `core/risk.py`: A6 bounds (`bound_violations`); §2A account-wide limits in `check_entry` (freeze, sleeve kill switch, −5% daily stop, same-symbol block, 6 positions, per-strategy caps, 35% per symbol, 50% per group with all crypto one group, settled sleeve cash); size = min(risk, cash, symbol room, group room), every pass carries a `risk_check_id`; `assert_live_ready` → `LiveNotReady` listing every problem.
- `tenancy/config.py`: `TenantConfig` (limits, approved versions, sectors) loaded from the tenant's repo.
- MOM-01 v1.1 moved to `will-strategies` (spec JSON + `Mom01` class); reproduces the day-1 live order exactly (AAPL limit 348.94, stop 346.45).
- Checks: 68 platform tests + 9 will-strategies tests pass; ruff clean; mypy strict clean.

**Deviations / decisions taken (reason → consequence)**
1. Exposure limits **clip** the size instead of only blocking (architecture §2A said "blocked entry"). Reason: at today's size the 35% cap would otherwise block every Core trade → a trade that fits the limits still happens, smaller; blocks only when nothing fits.
2. Unknown stock sector = its own group (conservative; no sector map yet) → the 50% group cap only bites for crypto until sectors are filled in `will-strategies/config/tenant.json`.
3. `max_concurrent_positions` inside MOM-01's spec = 1 (day-1 "one position at a time"); the account allows MOM-01 up to 3 (E13). Will to confirm v1.1's own number.
4. Target in the intent is computed from the entry limit; the exit watcher (step 4) recomputes it from the fill (day 1 used the fill price).

**Findings for Will**
- With equity ≈ $150 and Core ≈ $100, the 35% per-symbol limit caps one MOM-01 position at ≈ $52 (half of Core's cash). The scheduled stocks run does not apply the 35% rule (engine-only), so live behaviour today is unchanged.
- MOM-01 has no validation run → `expected_signals_per_week` unset → the engine will refuse MOM-01 live until it is measured (backtest plan v3) or Will sets an interim value.
- VOL-01 has no monthly loss cap; A6 requires one on every sleeve (≤ 50%) before VOL-01 moves onto the engine.

**Follow-up (Will 11:20)**
- Small-account exposure tier: below $1,000 equity the caps are 70% per symbol / 80% per group; from $1,000 they revert to 35% / 50% (`AccountLimits.small_account`, set in `will-strategies/config/tenant.json`). Reason: Will chose to raise the caps while the account is small → MOM-01 can use Core's full cash again (cash binds, ≈ $100).
- MOM-01 spec keeps `max_concurrent_positions = 1`: Core cash (~$100) funds one position at 1% risk anyway; the account ceiling stays 3 for when Core grows (revisit at Core ≥ ~$300).

## 2026-10-31 — Pre-step-3: build moves to SDE, tzdata, event chain IDs, unknown-version failure
The build moved from the Claude Desktop cloud workspace to Claude Code working directly in `SDE` (hand-over point `9ba2c2e` / `01d5013`; Will pulled and tested step 2 on the laptop). Live trading stays in the Cowork scheduled tasks.

**Done**
- Added `tzdata` to `dependencies`, for all platforms. Step 2 crashed on Windows at import (`ZoneInfoNotFoundError` from `core/bars.py:15` and `tests/conftest.py:17`): Windows has no system time zone database, and the earlier runs were on Linux. Declaring it everywhere also means the Lambdas don't depend on their base image.
- Added nullable `correlation_id` and `causation_id` to the envelope (PIOS ADR-011, ADR-020), since stored events can't be backfilled.
- The store now raises `UnknownEventVersion` on read for any version other than the current one (PIOS ADR-013). An unknown event type already fails at read with a pydantic `ValidationError`; a test now pins that.
- README: doc paths updated after the docs split between `pios-algo/docs` and `will-strategies/docs`.
- Checks (Will ran them on Windows, Python 3.13, with `tzdata` already installed by hand in that `.venv`): 81 platform tests + 9 will-strategies tests pass; ruff clean; mypy strict clean.

**Deviations / decisions taken (reason → consequence)**
1. The envelope stays v1 despite the new fields. No event database exists yet, so no stored event needs upcasting → once real events are stored, any further field change needs a version bump and an upcast path (ADR-013).
2. `append` also refuses unknown versions, which the plan's read-only rule didn't cover. The log is append-only, so an unreadable event could never be removed → a bad event fails its whole batch before anything is written.

**Python targets**
- Engine runs on 3.15, Lambdas on 3.14 (the newest managed runtime found, per PIOS ADR-020), so `requires-python` is `>=3.14` in both repos, with ruff and mypy targeting that floor. This replaces step 1's `>=3.10`, which only existed for the cloud chat's linked Python 3.10 shell → that shell can no longer run these repos, and no longer needs to now the build lives in SDE.
- First run on 3.15.2 (Will, Windows): 81 platform tests + 9 will-strategies tests pass; will-strategies ruff clean. pios-algo ruff failed on UP042 (`EventType(str, Enum)`), a rule the py314 target turned on, which also stopped that run before mypy started.
- Fix: `EventType(StrEnum)`. It changes `str(member)` from `EventType.OrderPlaced` to `algo.OrderPlaced`, but all code compares members or reads `.value`. Rejected: silencing the rule, which keeps the old pattern for no benefit.
- Status at this entry: rerun on 3.15.2 after the fix: 81 tests pass, ruff clean, mypy strict clean on its configured packages (11 source files). Committed as `a83ab5f`, will-strategies as `c1fc3b7`. will-strategies has no mypy in its dev tools or config, so mypy doesn't apply there. 3.14 itself hasn't been run. The dependencies resolve for 3.15 and 3.14 on Windows and `pydantic` for 3.14 on Linux (`uv pip compile --only-binary :all:`), which shows they can install but tests nothing.

**How step 2 reached the laptop**
1. The hand-over said the bundles in `SDE` held `9ba2c2e` / `01d5013`. `git bundle list-heads` showed `a0d4005` / `df5c951`: valid bundles, one commit short, with no small-account tier. A pull would have succeeded and left MOM-01 on the 35% cap with no error.
2. Root cause, per the algo chat: its tool reported the re-sent files as written, but the laptop copies were never replaced. It reissued them as `*-step2b.bundle`, which checked out: correct heads, step 1 as prerequisite, fast-forward in throwaway clones, E15 values present. Lesson: check delivered files on the machine that receives them.
3. Private docs split out before the pull: state, handoff and planning notes went to `will-strategies/docs/` (untracked, not gitignored there), architecture and brief stayed in `pios-algo/docs/` (untracked). No account-ID-like value appears in `pios-algo` files, history or the bundle.

**Rebuilding `.venv` on Windows**
```bash
# Git Bash, from terra-initiative-home/pios-algo. PowerShell 5.1 has no && and Git Bash strips backslashes.
uv venv --python 3.15 --seed --clear .venv     # --seed: pip is needed for the install below
.venv/Scripts/python -m pip install -e ".[dev]"
```
- First attempt failed with `failed to remove directory ...\.venv\Scripts: Access is denied. (os error 5)`. VS Code's isort and Pylint extensions were running from `.venv\Scripts\python.exe`, which locks it; the failed rebuild had already deleted most of `.venv`.
- Fix: VS Code → **Python: Select Interpreter** → an interpreter outside `.venv`, wait for the extensions to restart, rebuild, then select `.venv` again.

**Known limitations / next**
- `.venv` rebuilt on 3.15.2 in both repos, after the move below.
- Next: step 3, the Webull adapter on paperTrade keys. Blocked until Will generates the keys.
- Done: `pios`, `pios-algo` and `will-strategies` moved into `terra-initiative-home`, all three in its `.gitignore` because that repo has GitHub and Bitbucket remotes and `will-strategies/docs` holds private data. That `.gitignore` change and HUB.md Machine Paths are still to be updated at the next sync.
- Both repos stay local until the Terra GitHub org exists.
