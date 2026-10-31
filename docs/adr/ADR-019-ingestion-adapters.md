# PIOS ADR-019: Ingestion Adapters & Observed-vs-Derived Reconciliation

> Copied 2026-10-31 from Notion: https://app.notion.com/p/40789370d497819dbd05f0a25bd92f86

> **Edited copy.** Will's personal account list, debts, baselines and housing details are left out of this repo (ADR-016 §7: values live on their own pages; algo ADR-002: personal data stays out of Terra's code). Omissions are marked. Notion has the full text.

**Status:** Proposed — 2026-10-27 (design approved by Will in chat; PIOS is pre-coding, learning gate still applies)

**Service:** PIOS

**ADR sequence:** PIOS ADRs — 019 (local sequence)

**Answers:** ADR-015 open items — parsing rules, workflow shape, bucket mapping, error handling (CRR formula stays open)

---

## Context

The PIOS tracker pulls balances, spending, cashback and credit scores into one Wealthfront-style dashboard that tracks actuals against the active Year Baseline parameter set. Hard constraints (Will, 2026-10-26): no paid aggregators (SimpleFIN / AwardWallet skipped); PIOS never logs into accounts or scrapes private APIs; no new automations — recurring work goes into existing ones (Make scenario 5199173 gets new routes only). Sources are therefore files, parsed emails, a manual monthly form and two existing feeds — each fragile in its own way, so ingestion must be modular, idempotent and fail loudly (ADR-013).

---

## Decision 1 — Ingestion adapters (one Lego brick per source)

Every adapter implements the same contract:

- **Input:** one source + one format
- **Field allowlist:** permitted `field_key`s, each with a unit. Keys are `institution.account.metric`
- **Idempotency key:** source + external ID, enforced by a unique index on the event store — re-imports never duplicate
- **Reject path:** anything off the allowlist or missing a required field becomes an `IngestionRejected` event in a review queue; nothing is dropped silently (ADR-013)
- **Health:** last-success time + expected cadence → freshness on the dashboard

| Adapter | Covers | External ID |
| --- | --- | --- |
| Savings export | One savings account: balance + interest | QFX `FITID` preferred; CSV fallback = hash of account + date + amount + description + position among identical rows in the file |
| Email parser (Make 5199173, new routes) | Cashback, credit score alerts, statement balances (points/miles) | Gmail message ID + field key (one email can carry several fields) |
| Manual monthly snapshot | Per-account monthly spend totals, debt balances, anything not covered above | form + field key + month; a resubmission is a `supersedes` correction, not a duplicate |
| Trade-email log | Brokerage fills (existing route) | Gmail message ID |
| Webull connector | Positions / orders | order ID, or position + as-of date |

**Gemini output is untrusted:** PIOS validates it against the allowlist (not Make) and stores the raw snippet + message ID for audit.

**Line source map:** exactly one authoritative source per budget line per month, so an itemized feed and a snapshot total never double-count. A later itemized adapter replaces the snapshot for that line by changing the map, not the events.

---

## Decision 2 — Spending data: snapshot totals now, exports later (Will, 2026-10-27)

No adapter covers most day-to-day spending. Because routing gives most cards one category, a card's monthly total ≈ its budget line's actual. **Option A now:** the manual snapshot form takes one monthly total per account; **Option B later:** add a per-account export adapter only where itemized detail proves worth it. Per-purchase alert emails (option C) rejected — one Make run per purchase, credits already exhausted.

*[Omitted: the per-account snapshot form field list. See Notion.]*

---

## Decision 3 — Events

**Envelope (all events):** `event_id`, `type`, `schema_version` (ADR-013 upcasting), `occurred_at` vs `recorded_at`, `source{adapter, version}`, `idempotency_key`, `causation_id`. Money in integer cents; points/miles as integers tagged with their program; no floats.

- **`BalanceObserved`** `{source, field_key, value, unit, observed_at, supersedes?}` — point-in-time fact from a statement, email or snapshot
- **`TransactionRecorded`** `{account, posted_at, amount, merchant, status: pending|posted, line_key, granularity: item|monthly_total}` — only posted transactions count toward balances
- **`CashbackEarned`** `{program, amount, unit, status: pending|posted|reversed, txn_ref?}` — a reversal is a new event, never an edit
- **`CreditScoreObserved`** `{model, bureau, score, band, directional: true}` — separate from balances (not summable; own band logic)
- **`SweepRecommended`** → **`ExcessSwept`** `{month, lines[], amount, destination, param_set}` — `ExcessSwept` only once the move is confirmed (PIOS stays advisory-only, ADR-016)
- Supporting: `IngestionRejected`, `ReconciliationDriftDetected`, `BalanceAdjusted{reason}`

---

## Decision 4 — Observed vs derived reconciliation

1. Derived balance = last observed balance + posted transactions since.
2. At each new observation: drift = observed − derived.
3. Drift within the per-account tolerance (a parameter — no hard-coded value, ADR-016) → period closes.
4. Over tolerance → `ReconciliationDriftDetected` to the review queue; fixed by importing the missing transactions or an explicit `BalanceAdjusted`. Nothing is overwritten silently.
5. Display: observed = "as of [date]"; derived = "~now".
6. Points: the change between statement balances is checked against `CashbackEarned` minus redemptions.
7. Reconciliation is a projection — deterministic from events, rebuilt manually per ADR-014.

---

## Decision 5 — Parameter sets, sweep and shortfall (Will, 2026-10-26/27)

*[Omitted: the specific parameter sets, their amounts, the switch conditions by account and the housing override. See Notion.]*

- **Parameter sets** inherit: a line's effective value = the set's override, else its parent's value.
- **Switching sets** is a `ParameterSetActivated` event, triggered by `ModeChanged`; never inferred.
- **Line types:** card-anchored (exact; alerts both directions — underspend breaks the card math) · padded (creep alert when actual passes the baseline amount) · unlocked (alert only above its own amount).
- **Sweep = netted:** Σ(budget − actual) across padded lines; overspends offset underspends, so it never reports money that doesn't exist. Provisional until every adapter for the month has reported.
- **Shortfall rule:** if the net is below zero → sweep $0, shortfall alert shown (never hidden).
- **Sweep destination comes from the Mode Gate (ADR-017).**

---

## Projections & dashboard (summary — detail on doc 24)

- **Baseline Tracker** — actuals vs the active set, creep alerts, month-end sweep.
- **Card pay-for-itself tracker** — per card per card-year (fee date): fee − credits − perks − rewards premium over the catch-all rate; point value per program; paced alert ahead of the fee date.
- **Repair Mode view** — collections by ROI (Est. Score Gain ÷ agreed amount; manual fallback order while Est. Score Gain is blank), debt avalanche, gate progress (`ModeGateConditionMet` asks, never flips), score trend labeled directional.
- **Dashboard (one screen):** mode chip + gate progress · net worth hero (observed, as-of) · tiles: month vs plan ($ + %, labeled by baseline) / sweep / score · swappable panel (Repair: collections + avalanche; Growth: allocation vs bands, **%-only**) · card strip · freshness + review-queue footer. **Display rule (Will, 2026-10-27):** splits/allocations in %, observed balances in $.

---

## Consequences

**Positive:** every source plugs in or out alone (Lego); re-imports are safe; drift is visible instead of silently absorbed; works from day one with a 5–10 minute monthly form.

**Negative:** spending is coarse (monthly totals) until per-account exports are added; email parsing stays fragile; the month's sweep waits on the slowest source.

**Deferred:** per-account export adapters (option B); CRR formula (ADR-015).

---

## Related

ADR-011 · ADR-013 · ADR-014 · ADR-015 · ADR-016 · ADR-017 · 24 — Finance Strategy → PIOS Implementation Map
