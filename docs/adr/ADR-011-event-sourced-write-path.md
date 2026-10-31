# PIOS ADR-011: Event-Sourced Write Path / Projection-Based Read Path

> Copied 2026-10-31 from Notion: https://app.notion.com/p/39c89370d497813eb743ee57faac7a5f

> 2026-10-23 note: "ADR sequence: Terra Engineering HQ — 011" (same on 012–014) is the old label — these belong to the local PIOS ADR sequence (001–018), same as ADR-015 onward.

**Status:** Accepted

**Date:** 2026-05-30 (decision made, per PIOS Current State) — formalized as a standalone ADR 2026-07-13

**Service:** PIOS

**ADR sequence:** Terra Engineering HQ — 011

---

## Context

PIOS is designed as an event-sourced financial intelligence system — every capital-affecting action must produce an immutable, replayable record (per PIOS ADR-007: Decision Records Are Immutable and Mandatory). That requires a concrete write/read architecture, not just the principle.

---

## Decision

**Write path is the event log; read path is materialized projections built from it.** The 14-table event-sourcing schema (`pios_schema_v1.0.0`, 6 layers) is the single source of truth — nothing is written directly to a read model. Projections are derived, rebuildable views over the event log, never the system of record themselves.

Every event carries **correlation and causation IDs**, enabling full request-chain reconstruction across PIOS and, where applicable, Terra API (see Terra API ADR-007: Audit Log Bus, which explicitly extends this same correlation-ID architecture to the platform level).

---

## Consequences

**Positive:**

- Full historical replay is possible by construction — not bolted on
- Read models can be rebuilt from scratch at any time if a projection is wrong or a bug is fixed retroactively (see ADR-014)
- Causal chain reconstruction across services, not just within PIOS

**Negative:**

- More moving parts than a direct CRUD model — accepted as the cost of the auditability PIOS's whole design brief requires

**Deferred:**

- None — foundational, not phased

---

## Related

- PIOS ADR-007: Decision Records Are Immutable and Mandatory (this ADR is the concrete implementation of that principle)
- ADR-013: Event Schema Versioning (governs how the event log evolves over time)
- ADR-014: Projection Rebuild Strategy (governs how the read side is regenerated from this write path)
- Terra API ADR-007: Audit Log Bus (shares the correlation/causation ID architecture)
