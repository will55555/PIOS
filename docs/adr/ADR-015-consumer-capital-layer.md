# PIOS ADR-015: Consumer Capital Layer — Cashback Ingestion & CRR Tracking

> Copied 2026-10-31 from Notion: https://app.notion.com/p/39c89370d497816e9cfded22f3ce1928

> 2026-10-27: ADR-019 (Proposed) answers this ADR's open items on Gmail parsing rules, the Make workflow shape (new routes on scenario 5199173, no new automation), bucket mapping, and error handling (reject queue, fail loudly). The **CRR formula stays open**.

**Status:** Accepted (design-level) — formalized as a standalone ADR 2026-07-13

**Date:** Design phase, predates 2026-07-13 (exact date not recorded in source)

**Service:** PIOS

**ADR sequence:** PIOS ADRs — 015 (local sequence)

---

## Note on source material

Unlike ADR-011–014, which each had a dedicated Obsidian design file, this decision exists only as a one-line summary in the PIOS README: *"Consumer capital layer — Gmail ingestion, cashback events, YTD savings projections, CRR trend."* The **what and why** below is a faithful expansion of that line and PIOS's established architecture (event sourcing, intent-based buckets). The **how** — exact Gmail parsing rules, the Make/n8n workflow shape, the CRR formula itself — was never written down anywhere found in Notion or Obsidian. Treat the Decision section as directionally accepted, not implementation-ready; the open items below need real design work before coding starts.

---

## Context

PIOS's core design (ADR-001–014) governs *managed* capital — money deliberately allocated into intent-based buckets (Foundation, Growth, Income, Expansion, Speculative). But real personal finance also generates smaller, passive capital events that never get manually entered: credit card cashback, rewards redemptions, and similar recurring inflows that show up as emails, not as deliberate allocation decisions. Without a defined ingestion path, this capital is invisible to PIOS entirely — not tracked, not counted toward savings goals, not contributing to any intent bucket.

---

## Decision

**A consumer capital layer ingests cashback/rewards events from Gmail via Make + n8n automation**, converting them into PIOS event-log entries (per ADR-011's write-path-is-events model) rather than requiring manual entry. This makes small, passive capital inflows a first-class part of the event-sourced ledger, subject to the same immutability and audit-trail guarantees as deliberately-allocated capital.

Two projections (per ADR-011's read-side-is-projections model) are built from these events:

- **YTD savings projections** — running total of consumer capital captured for the year
- **Credit Recycling Rate (CRR) trend** — a tracked metric over time; the underlying formula is not yet specified

Build sequence positions this **after** the PIOS MVP and after Terra API Phase 3's WebSocket relay (per the PIOS README's build sequence) — it's an enhancement layer on top of the core event-sourced ledger, not part of the initial build.

---

## Open Items (not yet designed)

- Exact Gmail parsing rules — which senders/patterns count as a cashback/rewards event, how false positives are avoided
- The Make/n8n workflow itself — trigger, transform, and event-emission steps
- CRR formula — what "Credit Recycling Rate" actually computes
- How ingested events map to intent buckets (does cashback default to a specific bucket, or require classification?)
- Error handling for malformed/ambiguous emails — does an unparseable email get dropped, queued for manual review, or does ingestion fail loudly (consistent with ADR-013's "fail loudly, don't guess" precedent)?

---

## Consequences

**Positive:**

- Passive capital (cashback, rewards) becomes visible and auditable instead of silently uncounted
- Reuses PIOS's existing event-sourcing infrastructure (ADR-011) rather than needing a separate tracking system

**Negative:**

- Introduces an external dependency (Gmail + Make/n8n) into what was otherwise a self-contained event store — email parsing is inherently fragile compared to deliberate user input
- No error-handling model defined yet, and ADR-013 sets a high bar (fail loudly on ambiguity) that this layer will need to actually meet, not just aspire to

**Deferred:**

- Full implementation spec (see Open Items above) — this ADR captures direction, not a build-ready design

---

## Related

- ADR-011: Event-Sourced Write Path / Projection-Based Read Path (this layer's events and projections are instances of that pattern)
- ADR-013: Event Schema Versioning — Upcasting at the Repository Layer (precedent for "fail loudly" error handling this layer should follow)
- Terra API ADR-003 (shared pool): Auth & Identity Strategy — PIOS's Terra API WebSocket relay (Phase 3) precedes this layer in the build sequence
- Terra Nkap — possible future connection point if consumer rewards ever intersect with Terra's own loyalty currency (not currently designed, speculative)
