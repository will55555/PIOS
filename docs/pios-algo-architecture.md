# pios-algo — Architecture v0.6 (2026-10-31 11:40; v0.5 + settled values, ADR-003 merge-ready brick, small-account tier, build steps 1–2 done)

The Webull algo layer, built as a self-contained "Lego brick" that runs on AWS now and becomes PIOS's public, bring-your-own-strategy algo layer later (ADR-002). Its code may later merge into the PIOS repo; its engine never shares a process with PIOS (ADR-003). It follows PIOS's accepted decisions: event-sourced, FastAPI, SQLite (dev) → PostgreSQL (prod), repositories behind an abstract interface (ADR-012), upcasting at the repo layer (ADR-013), projectors with position tracking (ADR-014). Broker and language choices: ADR-001 (Accepted). Ownership boundary: ADR-002 v3 (Accepted). Merge rules: ADR-003 (Accepted). Reference spec: claude/reference/ai-trading-agent-master-spec.md; gap analysis: claude/link-review-findings-2026-10-30.md §4–5. Data sources: claude/pios-algo-data-layer-spec-draft.md (draft).

## 1. Principles
- **Pure core, swappable edges.** Strategy logic = pure functions behind a strategy interface. Everything that touches the outside world (Webull, Notion, push, storage) sits behind a port (interface) with adapters.
- **Events are the source of truth.** Every signal, order, fill, exit, deviation and kill-switch change is an append-only event. Positions, sleeve balances, tallies and tax are projections rebuilt from events. Day-1 JSONL imports through the upcaster.
- **Safety before features.** Platform bounds (ADR-002 A6), account-wide limits (§2A), kill switch, loss caps, sleeve separation and settled-cash checks are enforced in the engine, not in prompts.
- **Decision chain:** the AI proposes → the strategy engine evaluates → the risk engine authorizes or rejects → the execution engine acts → monitoring verifies → the journal records → Will sets the bounds. The AI can't change limits, permissions, approvals or freezes.
- **Claude reviews, the engine executes.** Scheduled Claude tasks shrink to: pre-market research, end-of-day review and reports, weekend brief.
- **The watchdog never runs on the box it watches.**
- **Runtime isolation (ADR-003).** Even after a code merge into PIOS, the engine and watchdog run as their own processes; a PIOS bug, deploy or migration can never block an exit.
- **Infra spend follows proven profit.** C is earned by net results (§4C).
- **Platform ≠ strategies.** The platform repo holds no tenant strategies; every record carries `tenant_id` (ADR-002 A1, §11).
- **No error ≠ healthy.** The system checks that it is actually working (§2C), not just that nothing threw.
- **Broker is truth.** Reconciliation trusts Webull over the journal (2026-10-31: a never-confirmed CRX #2 instruction was logged as open).

## 2. Repos and modules
### Repos (ADR-002 A1) — local in `C:\Users\solan\OneDrive\Desktop\SDE\` since 2026-10-31; GitHub remotes pending
| Repo | Owner | Holds |
| --- | --- | --- |
| `pios-algo` (Terra GitHub org, private) | Terra | Platform: engine, adapters, risk + bounds, events, projections, backtester, Lambdas, API, Terraform, generic indicators, `Strategy` interface |
| `will-strategies` (Will's personal GitHub, private) | Will | Specs + strategy code (MOM-01 done; VOL-01, MR-02, CRX, JMP-01, ERN-01, MOM-02, SPY-NA to come), `config/tenant.json` (limits, approvals, sectors), approval script, trading history (`data/events/`), wash-sale watchlist |
`claude/code/algo_lib.py` v1.1 is split as strategies move: generic helpers → `pios_algo.core.bars`; rule logic → `will_strategies`. algo_lib stays as-is while the scheduled runs use it.

### Modules in `pios-algo` (Python package `pios_algo`; ✅ = built)
| Module | Job | Ports it uses |
| --- | --- | --- |
| ✅ `core/strategy_api` | `Strategy` protocol (pure `evaluate(MarketContext) → [SignalIntent | Skip]`), `StrategySpec` (`designed_on`, `expected_signals_per_week`, `autonomy_level`, risk rules), `param_hash`, approval check | `StrategySource` (git ref / S3 / SSM) — later |
| ✅ `core/bars` | generic, tenant-neutral helpers (VWAP, ATR, opening range, R, RTH filter); every output finite or `InvalidIndicator` | none |
| ✅ `core/risk` | A6 bounds, account-wide limits (§2A) incl. small-account tier, sizing clipped to limits, `risk_check_id`, live readiness gate (`LiveNotReady`) | none |
| ✅ `tenancy` | tenant id validation, per-tenant paths, `TenantConfig` (limits, approvals, sectors); KMS key per tenant — later | `SecretStore`, `TenantRepo` — later |
| ✅ `events` | envelope v1 (`algo.*`) + append-only store + legacy upcaster | `EventStore` (✅ SQLite; Postgres later) |
| `projections` | positions, orders, sleeve ledger, tallies, tax set-aside, infra-cost-vs-profit ledger, execution-quality and signal-frequency read models | `EventStore`, `ReadModelRepo` |
| `adapters/webull` | official Webull OpenAPI SDK: bars, snapshots, orders, account; MQTT stream later | `MarketData`, `Broker` |
| `adapters/data` | long-history sources per the data-layer draft (Coinbase, Kraken/Binance, CoinGecko) | `MarketData` |
| `adapters/notify` | push (iPad), Notion log writer | `Notifier`, `Journal` |
| `runner` | market-hours scheduler (APScheduler), polling loop, exit watcher | all ports |
| `monitor` | silent-failure checks (§2C) | `EventStore`, `Notifier` |
| `api` | FastAPI: status, positions, kill switch, pause/resume, approve — the cockpit and later PIOS's integration point | `EventStore`, read models |
| `lambdas` | watchdog, fallback exit watcher, data downloader, reconciliation, EOD report (same `core`) | same ports |

### 2A. Account-wide risk limits (E13 values confirmed 2026-10-30 23:20; small-account tier 2026-10-31) — ✅ built
Checked before **every** entry, across all strategies and sleeves, after the per-trade and per-sleeve checks. **Live refuses to start if any is unset.** Exposure limits **clip the order size** to what fits; an entry is blocked only when nothing fits (decided 2026-10-31 — at today's size, block-only would stop every Core trade).
| Limit | Value |
| --- | --- |
| Max concurrent positions (account) | 6 (MOM-01 ≤ 3, VOL-01 ≤ 3) |
| Max exposure per symbol (all strategies combined) | 35% of equity — **70% while equity < $1,000** |
| Max exposure per correlated group (sector; all crypto = one group; unknown sector = own group) | 50% of equity — **80% while equity < $1,000** |
| Same symbol in two strategies at once | blocked |
| Max buying-power use | settled cash only, per sleeve (cash account, no margin) |
| Account daily loss stop | −5% of start-of-day equity → no new entries that day |
| Emergency freeze | Will only; the AI can detect and report, never lift |
| Sleeve kill switch | blocks entries for that sleeve |
A blocked entry emits `algo.SignalBlocked{reason: "account_limit:<which>" | "sleeve:<which>" | "freeze"}`. Values live in `will-strategies/config/tenant.json`.

### 2B. Execution analytics (E13 — lesson 4)
Every order records: strategy decision time, submit time, broker acknowledgement time, requested price, decision-time mid, requested vs filled quantity, fill price(s), spread at decision and at execution, partial fills, rejection code, cancel outcome, price 5 and 30 min after exit; every trade records MFE/MAE. The execution-quality projection compares live costs with the backtest assumptions per instrument, session and volatility regime; the weekly report flags any instrument whose live cost exceeds the assumption by > 50%. Broker scorecard (ADR-001): execution quality / technical reliability / operational safety.

### 2C. Silent-failure monitor (E13 — lesson 2)
- **Signal-frequency drift:** each spec carries `expected_signals_per_week` from validation; alert if live is < 0.25× or > 3× over a 2-week window (or zero signals for 5 sessions when ≥ 1/week is expected). A spec without it can't go live (✅ enforced by the readiness gate).
- **Indicator validity:** any NaN/None/inf in a decision input blocks the signal → `algo.DeviationLogged{type:"invalid_indicator"}` (✅ helpers raise; envelope rejects non-finite payloads).
- **Risk check ran:** every live/paper `algo.OrderPlaced` must reference a `risk_check_id` (✅ envelope rule; the risk engine issues one per pass).
- **Data freshness:** stale quote (older than the strategy's budget in the timing doc) → no entry.
- **State match:** broker positions/orders/cash vs ledger reconciled at start, every 15 min in market hours, after any reconnect; mismatch → stop new entries + alert; broker wins; never-confirmed instructions are closed out as revoked/expired.
- **Live vs tested inputs:** spec version + `param_hash` logged on every signal; a spec not approved at its exact hash is refused (✅ built).

### 2D. Autonomy levels (E13 — promotion rules confirmed 2026-10-30 23:20)
Per strategy, stored in its spec; only Will promotes (`algo.AutonomyLevelChanged` requires `source="will"` — ✅ enforced).
| Level | Who acts | Promotion rule |
| --- | --- | --- |
| L0 Paper | engine/Claude on paper only | passes untouched test (backtest plan §0/§3) |
| L1 Propose | AI proposes, Will places | ≥ 10 paper/forward trades following rules |
| L2 Send + confirm | Claude/engine sends, **Will confirms in the Webull app** | reaches its review point (MOM-01 30 / VOL-01 20 trades) with net R ≥ 0 after costs and no rule breaks |
| L3 Engine executes | engine sends without per-order confirmation, inside all limits | L2 review passed + game-day failure tests passed + Will's written approval |
Today: MOM-01 = L2; **VOL-01 = L2 — in-app confirmation stays mandatory until its 20-trade review** (the crypto task's "Skip all approvals" covers Claude's tool permissions only). Paper set = L0. The readiness gate refuses L0 specs for live.

## 3. Event envelope v1 (✅ built — `schemas/event-envelope.v1.json`)
```json
{"event_id":"uuid","tenant_id":"will","stream":"trade|sleeve|system|signal","stream_id":"MOM-01#2026-11-02#AAPL","type":"algo.OrderPlaced","version":1,
 "ts":"2026-11-02T10:45:49-05:00","payload":{...},"meta":{"source":"engine|lambda|claude|will","strategy":"MOM-01","strategy_version":"1.1","param_hash":"…","sleeve":"core","mode":"live|paper|shadow|backtest","autonomy_level":"L2","rule_ref":"§4","risk_check_id":"uuid","host":"spot|ondemand|lambda|claude|local","broker":"webull","account":"…"}}
```
Rules: tz-aware `ts`; no NaN/inf in `payload`; live/paper `algo.OrderPlaced` needs `risk_check_id`; `algo.AutonomyLevelChanged`, `algo.FreezeSet`, `algo.FreezeLifted`, `algo.KillSwitchReset` only from `source="will"`.
Core types (all prefixed `algo.`): SignalDetected, SignalBlocked, RiskCheckPassed, OrderPlaced, OrderAcknowledged, OrderConfirmed, OrderPartiallyFilled, OrderFilled, OrderRejected, OrderRevoked, StopHit, TargetHit, TimeExit, PositionClosed, DeviationLogged, SleeveFunded, KillSwitchTripped, KillSwitchReset, DailyLimitHit, AccountLimitHit, FreezeSet, FreezeLifted, HostInterrupted, HostRecovered, FallbackEngaged, InfraCostRecorded, HostingTierChanged, BoundViolationBlocked, AutonomyLevelChanged; journal types for imported history: AccountSnapshot, DecisionRecorded, ConfigChanged, PositionChecked, ResultRecorded, AnalysisRecorded, NoteRecorded.
Store: one SQLite file per tenant (`data/tenants/<tenant>/events.db`), `algo_events` + `algo_schema_migrations`, append-only triggers, idempotent by `event_id`, optimistic concurrency per stream.

## 4. AWS layout — hybrid (Will's personal account, us-east-1; tenant #1 = `will`)
### 4A. Serverless layer (always on, ≈ $0–1/mo inside the permanent free allowances) — may trade real money
- **EventBridge Scheduler → Lambda (Python, arm64):**
  - `watchdog` — every 1 min in market hours (every 5 min 24/7 for crypto): reads the engine heartbeat; stale > 2 min with open positions → push alert (SNS) + engage the fallback exit watcher; checks the kill-switch flag and the freeze.
  - `fallback_exit_watcher` — only when engaged: polls positions + quotes each minute, applies the same stop/target/time-exit rules, sends **live** exits. Exits/flattens only — never opens. Webull individual keys need no IP whitelist, so the fallback can trade.
  - `downloader` (daily bars/stats → S3), `reconcile` (broker vs ledger), `eod_report`.
- **DynamoDB (on-demand, small):** heartbeat, kill-switch flag, freeze flag, engine lease (one active host at a time), keyed by `tenant_id`.
- **S3:** `s3://pios-algo-<acct>/tenants/<tenant>/…` — event-store backups (every 5 min in market hours + on interruption), bars, reports; lifecycle rules.
- **Secrets (ADR-002 A4):** SSM SecureString `/pios-algo/<tenant>/{paper|live}/*`, encrypted with a **per-tenant KMS key** (≈ $1/mo); only the tenant runtime role can decrypt; CloudTrail alert on any other decrypt. No human operator role has decrypt.

### 4B. Engine on Spot — paper, shadow AND live money
- Auto Scaling group of 1, **Spot**, mixed types (t4g.micro → t4g.small → t3.micro) across several AZs with capacity rebalancing; Ubuntu arm64, systemd; AMI + user data from Terraform.
- Runs `runner`, `monitor` and `api`; loads tenant `will` strategies from `will-strategies` at a pinned, approved git ref.
- On the 2-minute interruption notice: emit `algo.HostInterrupted`, flush SQLite to S3, release the lease → the watchdog engages the fallback. On boot: restore SQLite from S3, **reconcile with the broker first**, take the lease.
- **Fail closed on live money:** while the engine is down, no new entries; only the fallback may exit. Host not back within 10 min in market hours → iPad alert with the manual flatten runbook.
- No Elastic IP needed. ≈ $2–3 compute + $3.65 public IPv4 + ≈ $0.65 for 8 GB gp3 → **≈ $7/mo**.

### 4C. Step up: on-demand — only when profits justify it (gate confirmed 2026-10-30 23:20)
- Same AMI, one Terraform variable: `capacity = "spot" | "ondemand"`. **Chosen variant: C-scheduled** (market hours only, crypto stays on A) ≈ $6–8/mo all-in; C 24/7 ≈ $12.26/mo for the instance.
- **Profit gate:** move to C only when **all** hold: (1) trailing 3 calendar months net P&L after **all** costs (AWS, data plan, fees, spreads) ≥ **3× C's extra monthly cost**; (2) ≥ 2 of those 3 months net positive incl. the latest; (3) ≥ 30 live trades in the window. **Step back down** after 2 consecutive failing months.
- Reliability issues don't trigger C by themselves → fix within B first, log a `algo.DeviationLogged`, review at month end.
- The infra-cost-vs-profit ledger computes the gate monthly; the month-end report says "C justified: yes/no" with the numbers. Will approves.

### 4D. Common
- **Network:** no inbound except the API behind auth (or SSM Session Manager / tunnel; no SSH open).
- **Ops:** CloudWatch logs + alarms (heartbeat missed, kill switch tripped, freeze set, fallback engaged, bound or account-limit violation, signal-frequency drift, invalid indicator, state mismatch, unexpected KMS decrypt); budgets per claude/aws-cost-cut-plan.md ($45 account / $30 `project=pios-algo`); Terra boxes in the same account tagged `owner=terra` (ADR-002 A3).
- **Daily report (E13):** equity, realized/unrealized P&L, open positions/orders, exposure by symbol and group, daily drawdown, signals / executed / rejected / skipped, risk interventions, API and execution errors, fees + slippage, strategy versions + autonomy levels, deviations. Never only winners or a headline win rate.
- **Deploy:** `pios-algo` → GitHub Actions → Lambda zip + AMI/user data; Terraform applies. `will-strategies` deploys by bumping an approved ref in tenant config. Claude can push code; it never sees the keys.

### 4E. Monthly estimate
| Setup | Est. monthly |
| --- | --- |
| A only (Lambda polling, no box) | ≈ $0–1 |
| **A + B (paper, shadow and live — chosen) + 1 KMS key** | **≈ $8–10** |
| A + C-scheduled (if the profit gate passes — chosen variant) | ≈ $7–9 |
| A + C 24/7 | ≈ $19–21 |
All leave room under the $30 cap for the Webull OpenAPI stock-data plan.

**Updated 2026-10-31 (Will, E16):** start with A only at a ≈ $10 cap until a strategy has earned more. The tables above stay as the upgrade path.

## 5. Build order (status 2026-10-31)
1. ✅ **Done 10/31** — two repos; `tenant_id` everywhere; envelope (incl. `risk_check_id`, `param_hash`, `autonomy_level`); SQLite event store; import of the 10/30 JSONL (64/64). pios-algo 2af7a93 / will-strategies e653f77.
2. ✅ **Done 10/31** — `Strategy` interface + spec loader (`designed_on`, `expected_signals_per_week`, `autonomy_level`); `param_hash` + approval; MOM-01 in `will-strategies` (reproduces the day-1 order); A6 bounds + account-wide limits (§2A) + small-account tier; live refuses to start with any limit unset. pios-algo 9ba2c2e / will-strategies 01d5013 (bundles for Will to pull).
3. Webull adapter against **paperTrade** keys (per-tenant KMS/SSM). Check: key scopes (no withdrawals?), OAuth/delegated option. **Blocked on the keys.**
4. Exit watcher in `core` (shared by engine + fallback Lambda; target recomputed from the fill); execution analytics fields on every order (§2B).
5. Serverless layer: heartbeat, lease, watchdog, kill-switch + freeze flags, alerts.
6. `monitor` (§2C): validity, risk-check-ran, freshness, reconciliation (broker wins), signal-frequency drift.
7. Spot engine with interruption handling; game-day tests on paper (kill mid-position → fallback exits; stale data; API disconnect; rejected order; partial fill), then once on live with the smallest position.
8. Kill switch + loss caps + sleeve ledger + infra-cost ledger as projections; FastAPI status + kill endpoint; daily report.
9. MOM-01 on paper → compare with the Claude-run paper results for a week → live keys on A + B at its current autonomy level (L2). Needs: Will's approval of the spec + `expected_signals_per_week`.
10. VOL-01 (needs a monthly loss cap, A6), paper strategies, CRX; backtest runner using the same `core` (backtest plan v3); data-layer adapters (draft spec).
11. PIOS integration: `git subtree` into the PIOS repo at `pios/algo` (ADR-003), event stream + read models; runtime stays separate. Multi-tenant hardening (Postgres row-level security, tenant onboarding, ToS) only before user #2 (ADR-002 §11).

## 6. Open decisions (Will) — 2026-10-31
- MOM-01: approve v1.1 at its `param_hash`; `expected_signals_per_week` — measure via a backtest (plan v3) or set an interim value.
- VOL-01: a monthly loss cap ≤ 50% (A6) before it moves onto the engine.
- Webull: key scopes (withdrawals?), OAuth/delegated access — at paperTrade key generation.
- Paid OpenAPI stock-data plan ("Advanced Quotes") price → E3/E4.
- PIOS learning gate + shared event core (asked in claude/pios-scaffold-seed-prompt.md).
- Resolved: personal AWS account (E1); Terra GitHub org for the platform (E2); Python track (E6); hosting E11 + profit gate + C-scheduled; ADR-001, ADR-002 v3 + A6 (E12); E13 limits + autonomy rules; ADR-003 (E14); small-account tier + MOM-01 position limit = 1 (E15).
