# PIOS ADR-020: Event Core and the pios-algo Boundary

**Status:** Accepted (Will, 2026-10-31)

**Service:** PIOS

**ADR sequence:** PIOS ADRs — 020 (local sequence). Written in this repo first, then added as a child page of the PIOS Notion page.

**Related:** ADR-005, ADR-011, ADR-012, ADR-013, ADR-014, ADR-016, ADR-019; algo ADR-002 v3, algo ADR-003

---

## Context

pios-algo (Python package `pios_algo`, event envelope v1) is being built ahead of PIOS and will join this repo by `git subtree` at `pios/algo`. Two options existed for the event core: PIOS adopts `pios_algo.events`, or PIOS keeps its own envelope and reads algo events across a boundary.

Checking `pios_algo.events` against ADR-011, ADR-019 and the 6-layer schema note (2026-10-31) found that it cannot hold PIOS events as written:

- Event types are a closed `algo.*` list and streams are limited to `trade | sleeve | system | signal`. `PolicyParameterSet`, `LiabilityOpened` and `BalanceObserved` have nowhere to go.
- It has no `correlation_id` or `causation_id`, which ADR-011 and schema Layer 5 require on every event.
- It has no `recorded_at` or `idempotency_key`, which ADR-019 requires.
- Importing it from PIOS would break algo ADR-003, under which PIOS talks to algo only through its published schema and API, and live-trading code would have to change whenever PIOS changed its events.

---

## Decision

1. **PIOS owns its envelope** (`pios.events.Envelope`): `event_id`, `tenant_id`, `aggregate_type`, `aggregate_id`, `type`, `schema_version`, `occurred_at`, `recorded_at`, `source{adapter, version}`, `idempotency_key`, `correlation_id`, `causation_id`, `payload`.
2. **Payloads hold no floats** (ADR-019). Money is integer cents. Prices that cents cannot represent, such as a crypto limit of 0.00071, are decimal strings.
3. **Algo events cross through a repo-layer translator** that reads `schemas/event-envelope.v1.json`, in the same place and under the same rule as ADR-013 upcasting: an unknown type or version is a hard error. It converts float prices to decimal strings. It is designed here and not built.
4. **The boundary holds in both directions.** PIOS never imports `pios_algo` or `will_strategies` (enforced by `tests/test_boundaries.py`), and algo never imports PIOS (enforced by its own test). Algo never edits PIOS tables; PIOS never edits `algo_` tables. Each keeps its own migrations.
5. **Runtime stays separate** (algo ADR-003). The trading engine and watchdog run as their own processes, so a PIOS bug, deploy or migration can never block an exit. The watchdog never runs on the box it watches. Config is injected, with no globals.
6. **Never in this repo:** `will-strategies`, broker keys, and tenant data such as account numbers and balances (algo ADR-002 A1, A4, A7).
7. **Learning gate stays.** This repo is scaffold-only until Will clears or lifts the gate: skeleton, interfaces, stubs and CI, with no event types, projectors, rules engine, routes or tables.
8. **PIOS targets the latest Python, 3.15** (Will, 2026-10-31). This replaces the 3.10 floor in the seed prompt.

---

## How this reads against existing ADRs

Accepted ADRs are immutable, so these readings are recorded here rather than edited in.

- **ADR-016 §5, "execution happens outside PIOS":** "outside" means runtime, not repository. Housing algo code in this repo under Decision 5 does not violate it.
- **ADR-016 §5, adapters read parameters from PIOS:** pios-algo holds its own limits for now, in `will-strategies/config/tenant.json`. This is an accepted interim while PIOS has no parameter projection and no relay. Once both exist, the adapter moves to reading from PIOS, keeping ADR-016's safe fallback of stop or hold, never acting on stale values.
- **ADR-005, AI cannot execute trades:** the 2026-10-30 decision lets Claude send test trades with Webull cash. That is a scoped exception for the algo layer, bound by its autonomy levels (L0 to L3, promoted only by Will), the platform bounds and in-app confirmation at L2. PIOS itself stays advisory-only.

---

## Consequences

**Positive:**

- The algo build is not slowed or touched, and a PIOS change cannot reach live-trading code
- PIOS's envelope meets ADR-011 and ADR-019 from the first line
- Fills arriving through a translator matches ADR-016 §5 and ADR-019's ingestion model

**Negative:**

- Two envelope models and a translator to maintain
- Algo events logged before it gains correlation and causation IDs will have no chain, and events are immutable, so that history cannot be backfilled
- Python 3.15 has no confirmed AWS Lambda managed runtime yet (3.14 is the newest found), which affects algo's Lambdas, not PIOS

**Deferred:**

- The translator itself, built when PIOS first consumes algo events
- The 14 tables: no table-level DDL for `pios_schema_v1.0.0` could be found, so migrations start as modular empty baselines and tables arrive with the features that need them
