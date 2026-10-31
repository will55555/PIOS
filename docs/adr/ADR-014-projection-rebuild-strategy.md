# PIOS ADR-014: Projection Rebuild Strategy — Manual Rebuilds Only

> Copied 2026-10-31 from Notion: https://app.notion.com/p/39c89370d49781bd9828f5c96ac00be6

**Status:** Accepted

**Date:** 2026-05-30 (decision made, per PIOS Current State) — formalized as a standalone ADR 2026-07-13

**Service:** PIOS

**ADR sequence:** Terra Engineering HQ — 014

---

## Note on naming

The Terra Engineering HQ ADR index previously listed this slot as "Kill Switch Semantics." PIOS's own documented decision for ADR-014 is the **projection rebuild strategy**, not a kill switch — this ADR is titled to match what was actually decided. If "Kill Switch Semantics" was a separate real decision (plausible, given PIOS ADR-004's forced-shutdown-on-budget-exhaustion language), it hasn't been located and may need its own ADR number.

---

## Context

Projections (the read-side views built from the event log, per ADR-011) can become wrong — a bug in projection logic, a late-discovered upcasting error, or a new projection needed retroactively. The system needs a defined way to regenerate them.

---

## Decision

**Manual rebuilds only, with per-projector position tracking.** Each projector tracks its own position in the event log independently, so a rebuild replays events from the beginning (or from a known checkpoint) for one specific projection without disturbing others. Rebuilds are explicitly triggered, not automatic.

A **snapshot interface has been designed but deliberately not built yet** — full replay-from-zero is acceptable at PIOS's current data volume; snapshotting is deferred until replay time becomes an actual operational problem, not a theoretical one.

---

## Consequences

**Positive:**

- A bad projection can be fixed and regenerated without touching the event log (the source of truth) or other projections
- Per-projector position tracking means rebuilds are isolated — no cross-projection coordination needed

**Negative:**

- No automatic self-healing if a projection silently drifts — requires a human to notice and trigger a rebuild (acceptable given PIOS ADR-005: AI Is Advisory-Only, and manual oversight is the intended posture, not a gap)
- Full replay-from-zero could become slow as event volume grows — explicitly the trigger for building the deferred snapshot interface

**Deferred:**

- Snapshot interface (interface designed, implementation deferred until replay time is an actual bottleneck)

---

## Related

- ADR-011: Event-Sourced Write Path / Projection-Based Read Path
- ADR-013: Event Schema Versioning (a bad upcast is one of the reasons a rebuild would be triggered)
