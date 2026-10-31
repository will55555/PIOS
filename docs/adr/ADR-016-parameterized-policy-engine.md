# PIOS ADR-016: Parameterized Policy Engine — No Hard-Coded Financial Values

> Copied 2026-10-31 from Notion: https://app.notion.com/p/3fc89370d4978144a41fe28ac9830536

> 2026-10-23 note: the Deferred line "Parameter UI (Angular) — follows the frontend open item" — the frontend choice is already decided (PIOS ADR-018, Angular, accepted 2026-08-24). The Parameter UI itself is still deferred.

**Status:** Proposed (2026-10-17) — design-level; PIOS remains pre-coding behind the learning gate

**Service:** PIOS

**ADR sequence:** PIOS ADRs — 016 (local sequence)

**Decided by:** Will, 2026-10-17 (Finance Hub session)

---

## Context

The Finance Notion space holds a growing set of strategies (Core 55 automation ladder, Profit-Harvest waterfall, risk caps, Roth split, debt sequencing, bonus/match calendars, card routing). Each one carries specific numbers — 30% tax slice, 10% speculative cap, 95/5 Roth split — that change often. The PIOS design docs from May (04 Capital Allocation by Intent, 14 CAP, 17 Capital Allocation Ranges) also state fixed ranges. Will's rule (2026-10-17): **PIOS hard-codes no financial values. The user chooses the values; the backend runs the math. The same logic applies everywhere.** PIOS will also hand its values to execution tools — first the Webull algorithmic trading app — so those tools don't start from scratch.

---

## Decision

1. **Strategies are policy templates.** A template defines a rule shape (inputs → trigger → actions) plus a parameter schema (names, types, units, allowed bounds). It contains no default financial values.
2. **Values are user parameters, stored as events.** Setting or changing a value emits `PolicyParameterSet` (template, parameter, value, effective date, reason). The active parameter set at any moment is a projection over those events (per ADR-011), so every past decision can be explained with the values that were live at the time.
3. **Policy versions.** A coherent group of parameter changes is published as `PolicyVersionPublished` (e.g. moving from Phase 1 to Phase 2 of the Phase Ladder). The CAP's own versioning principle (doc 16) is implemented this way.
4. **The backend computes; it does not decide.** Projections calculate allocations, breaches, waterfalls and recommendations from events + the active parameter set. Output is `RecommendationIssued` / `AlertRaised` / `CapBreachDetected` — never an order. This keeps PIOS inside its existing guardrail: AI is advisory-only, and the Finance assistant is a watcher, not an actor.
5. **Execution adapters read the parameters.** Execution happens outside PIOS, in tools the user authorizes — the Webull algo app (OpenAPI), broker-native recurring buys (Robinhood), Make automations. Each adapter subscribes to the active parameter set for its template (via the Terra API relay, Phase 3) instead of holding its own copy of the values. Fills and results come back as events (`TradeExecuted`, `OrderRejected`, `StrategyTerminated`) through the ingestion path (the Gmail → Investment Log pipeline today; broker APIs later).
6. **Fixed rules stay fixed; numbers do not.** Structural safety rules are code, not parameters — e.g. position sizing reads settled cash, never margin buying power; unknown event versions fail loudly (ADR-013); speculative losses cannot draw on other intents (CAP firewalls). Only the numbers inside them are user-set.
7. **Existing numbers become "Will's parameter set v1".** Values on the Finance strategy pages and in PIOS docs 05/14/17 are treated as the first user configuration, not system constants. The strategy pages remain where those values live; PIOS docs reference them.

---

## Consequences

**Positive:**

- Strategy changes (which happen weekly) need no code change — only a parameter event
- Multi-tenant ready by construction: every tenant brings its own parameter set (fits ADR-012's schema-level tenancy)
- The algo app and other executors share one source of truth for limits; no drift between Notion, PIOS and the executor
- Full audit trail of *why* a value changed, not just what it is

**Negative:**

- Parameter schemas need careful bounds and validation, or a bad value becomes a bad recommendation
- Executors depend on the relay being up; each adapter needs a safe fallback (stop/hold, never act on stale values)

**Deferred:**

- Parameter UI (Angular) — follows the frontend open item
- Adapter contracts per executor — written when each executor is built (Webull first)

---

## Templates covered

See "24 — Finance Strategy → PIOS Implementation Map" (sibling page) for every template, its parameters by name, events, projections and the strategy page that holds Will's values.

---

## Related

- ADR-011 (event-sourced write path) — parameters are events like any other
- ADR-013 (upcasting) — parameter schemas version the same way event schemas do
- ADR-015 (consumer capital layer) — bonus/match/cashback templates live there
- ADR-017 (Liabilities & Mode Gate) — the debt-side templates
- Algorithmic Trading Layer — Webull (Finance Projects) — first execution adapter
- 14 — Capital Allocation Policy; 15 — AI Oversight & Automation Guardrails; 16 — Amendment, Versioning & Long-Term Stewardship
