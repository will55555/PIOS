# PIOS ADR-012: Repository Pattern — Swappable Persistence

> Copied 2026-10-31 from Notion: https://app.notion.com/p/39c89370d497814c9a68d7960d75a6fe

**Status:** Accepted

**Date:** 2026-05-30 (decision made, per PIOS Current State) — formalized as a standalone ADR 2026-07-13

**Service:** PIOS

**ADR sequence:** Terra Engineering HQ — 012

---

## Note on naming

The Terra Engineering HQ ADR index previously listed this slot as "Projection Update Strategy." PIOS's own documented decision for ADR-012 is the **repository pattern**, not projection updates — this ADR is titled to match what was actually decided. If "Projection Update Strategy" was a separate real decision, it hasn't been located and may need its own ADR number.

---

## Context

PIOS runs SQLite in development and PostgreSQL in production (schema-level multi-tenant). Without a clean boundary, persistence-layer differences between the two leak into business logic, making dev/prod behavior diverge in subtle ways.

---

## Decision

**Repository pattern: both DB implementations sit behind one abstract interface.** Business logic depends only on the interface, never on SQLite- or PostgreSQL-specific behavior. Swapping the underlying database is a repository-implementation change, not a business-logic change.

---

## Consequences

**Positive:**

- Dev (SQLite) and prod (PostgreSQL) stay behaviorally consistent by construction, not by discipline
- Swappable without touching the event-sourcing or capital-governance logic built on top

**Negative:**

- Abstraction layer adds indirection that a direct-DB-call approach wouldn't have — accepted given how central persistence correctness is to an auditable financial system

**Deferred:**

- None

---

## Related

- ADR-011: Event-Sourced Write Path / Projection-Based Read Path (the repository pattern persists both events and projections)
- PIOS ADR-008: Read-Heavy, Write-Restricted API Design
