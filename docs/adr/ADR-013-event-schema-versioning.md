# PIOS ADR-013: Event Schema Versioning — Upcasting at the Repository Layer

> Copied 2026-10-31 from Notion: https://app.notion.com/p/39c89370d497811c90e9daaccd665d50

**Status:** Accepted

**Date:** 2026-05-30 (decision made, per PIOS Current State) — formalized as a standalone ADR 2026-07-13

**Service:** PIOS

**ADR sequence:** Terra Engineering HQ — 013

---

## Context

Event schemas change over time as PIOS evolves. Old events in the log were written under an older schema version; the system must decide how to handle reading them once the schema has moved on — silently coerce them, or refuse.

---

## Decision

**Upcasting happens at the repository layer. Unknown event versions throw a hard error — no silent degradation.** When an event is read, the repository is responsible for transforming ("upcasting") it from its stored schema version to the current one before it reaches business logic. If a version has no known upcast path, the read fails loudly rather than guessing or skipping the event.

Consistent with PIOS ADR-010 (Safety Over Performance Is Non-Negotiable) — a financial system silently misinterpreting an old event is a much worse failure mode than a loud, immediately-visible error.

---

## Consequences

**Positive:**

- No silent data corruption from schema drift — failures are loud and immediate, not discovered months later in a wrong balance
- Upcasting logic is centralized at the repo layer, not scattered wherever events happen to be read

**Negative:**

- Every schema change requires an explicit upcast path to be written before old events remain readable — more upfront work than "just add a nullable field and hope"

**Deferred:**

- None — this was flagged as the most critical unresolved design decision before coding could begin; now resolved

---

## Related

- ADR-011: Event-Sourced Write Path / Projection-Based Read Path
- PIOS ADR-010: Safety Over Performance Is Non-Negotiable
