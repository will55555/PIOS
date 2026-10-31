# PIOS ADR-017: Liabilities & Mode Gate (Repair ↔ Growth)

> Copied 2026-10-31 from Notion: https://app.notion.com/p/3fc89370d4978181abd2c9f576f06d8e

**Status:** Proposed (2026-10-17) — design-level

**Service:** PIOS

**ADR sequence:** PIOS ADRs — 017 (local sequence)

---

## Context

PIOS's design (docs 04, 08, 14) only models *assets* across five intents (Foundation, Growth, Income, Expansion, Speculative). Will's live finance system runs a Repair Mode → Growth Mode loop (Financial Operating System: Credit Repair → Growth): debt and collections get fresh cash first, investing runs only on already-committed rails, and expansion is locked behind a gate. CAP §4.1's paycheck order (Foundation → Growth → …) also conflicts with "debt first". PIOS has no place for any of this.

---

## Decision

1. **Liabilities are a first-class aggregate.** Each debt or collection account is a liability stream with events: `LiabilityOpened`, `LiabilityPaymentRecorded`, `SettlementAgreed`, `LiabilitySettled`, `LiabilityRemovedFromBureau`. Balances are projections, not stored values.
2. **Payoff ordering is a pluggable sequencer.** Each liability group selects a sequencing method as a parameter (per ADR-016): e.g. ROI-rank (est. score gain ÷ agreed amount) for collections, avalanche (highest APR first) for standing debt, snowball as an option. The sequencer produces `PaymentRecommended` events; payments themselves are recorded from real activity.
3. **Mode is state derived from events.** The current mode (Repair, Growth, or any user-named mode) is a projection. A **Mode Gate** template defines the condition with user parameters — which liabilities count (e.g. "bad debt, federal student loan excluded"), and which flows are locked while the gate is closed. When the condition becomes true PIOS emits `ModeGateConditionMet` and asks for confirmation; the user's confirmation emits `ModeChanged` (never automatic — matches the Finance rule "confirm the flip, don't infer it").
4. **Mode selects the active policy version.** Each mode points to a policy version (ADR-016): its inflow waterfall, allowed intents, and exceptions (e.g. "Profit-Harvest gains stay in the brokerage even in Repair Mode"). The CAP §4.1 order and the Year Baseline waterfall become two user-defined waterfalls, one per mode.

---

## Consequences

**Positive:** the Repair/Growth loop, collections ROI ranking and avalanche order become computable and auditable; Growth-gated items (Roth, car, card stack, travel status) can be shown as locked with the exact remaining condition.

**Negative:** adds a sixth top-level concept beside the five intents; CAP docs need a note that liabilities sit outside the intent percentages.

**Deferred:** credit-score modelling (score gain per settlement is a user estimate parameter for now).

---

## Related

- ADR-016 (Parameterized Policy Engine)
- Financial Operating System: Credit Repair → Growth (Finance) — holds Will's current mode and values
- 14 — Capital Allocation Policy §4.1 (paycheck order) — becomes the Growth-mode waterfall
