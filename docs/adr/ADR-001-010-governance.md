# PIOS ADR-001 to ADR-010 — Governance

> Copied 2026-10-31 from Notion, "09 — Architecture Decision Records (ADR)": https://app.notion.com/p/36889370d49781388253c4a6e44d8492. Notion is the source; these ADRs share one page there.

## ADR-001: System Is a Capital Governance Engine, Not a Trading Platform

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** The system SHALL be designed as a **Capital Governance Engine**. Trading, execution, and assets are secondary concerns, subordinate to intent, time horizon, risk budgets, and rules.

**Consequences:** No real-time trading UI, no optimization for latency, no discretionary execution paths, all actions flow through governance layers.

---

## ADR-002: Time-Horizon Buckets as Hard Capital Firewalls

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** Capital SHALL be segregated into **hard time-horizon buckets**: 1-Year, 5-Year, 10-Year+. Buckets are firewalled: no implicit transfers, no shared risk budgets, no shared strategies.

**Consequences:** Capital mobility reduced by design. Code paths attempting cross-bucket access must fail hard.

---

## ADR-003: Intent Is Immutable by Default

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** Each CapitalUnit SHALL have an **immutable intent**. Reassignment requires explicit rule invocation and must generate a DecisionRecord with justification.

**Consequences:** No silent repurposing of capital. Increased friction for emotionally driven decisions. Clear audit trail.

---

## ADR-004: Risk Is Explicitly Budgeted and Enforced

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** Risk SHALL be modeled as a **finite, consumable budget**. Each bucket has its own RiskBudget. Strategies consume risk. Drawdowns decrement remaining budget. Budget exhaustion triggers forced behavior changes.

**Consequences:** Some strategies will be forcibly shut down. The system prefers inactivity over insolvency.

---

## ADR-005: AI Is Advisory-Only (Sensor, Not Actor)

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** AI SHALL be treated as a **signal sensor only**. AI systems cannot execute trades, move capital, modify rules, or adjust risk budgets. All AI output must pass through deterministic rules.

**Consequences:** Slower adaptation. Stronger explainability. Zero autonomous capital loss risk.

---

## ADR-006: Rules Engine Precedes All Execution

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** ALL capital-affecting actions MUST be gated by the Rules Engine. No component may execute directly, bypass rule evaluation, or self-authorize actions.

**Consequences:** More boilerplate, higher implementation cost, strong systemic safety.

---

## ADR-007: Decision Records Are Immutable and Mandatory

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** Every capital-affecting action SHALL generate an immutable DecisionRecord including: triggering signals, rules applied, assumptions, expected outcome.

**Consequences:** Increased storage requirements. Full decision replay capability.

---

## ADR-008: Read-Heavy, Write-Restricted API Design

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** The API SHALL be read-heavy by default, write-restricted, and explicit about intent and consequences. Most endpoints are observational, not mutative.

**Consequences:** UI is informational, not action-oriented. System safety increases at the cost of convenience.

---

## ADR-009: Paper Trading Before Any Real Execution

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** The system SHALL support simulation, paper trading, and replay-based backtesting before any real execution is enabled.

**Consequences:** Slower path to live trading. Higher confidence in rule correctness. Safer rollout.

---

## ADR-010: Safety Over Performance Is Non-Negotiable

**Status:** Accepted | **Date:** 2026-01-17

**Decision:** When safety and performance conflict, **safety always wins**. The system SHALL block ambiguous actions, refuse unsafe optimization, and preserve optionality.

**Consequences:** Missed upside is acceptable. Insolvency is not. This ADR supersedes all others in case of conflict.

---

## ADR Governance

- ADRs are immutable once accepted
- Changes require a **new ADR**
- Deprecated decisions remain documented
- Code changes must reference applicable ADR IDs
