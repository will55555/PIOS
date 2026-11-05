# pios-algo ADR-003 — Merge-ready brick: code may merge into PIOS, runtime stays separate

- **Status:** Accepted (Will, 2026-10-31 10:07 ET)
- **Related:** ADR-001 (Accepted), ADR-002 v3 (Accepted), architecture v0.5 §1 + §5 step 11, PIOS ADR-012/013/014

## Context
- Will (2026-10-31): pios-algo should be mergeable **into** PIOS (his Lego method), not only connected to it; one place is safer than things spread out.
- PIOS is still pre-coding; pios-algo's event core will likely be the first running PIOS code.
- Risk: live money needs exits to keep working. If the trading engine shared a process with the rest of PIOS, a PIOS bug, deploy or migration could stop it with a position open — against "protect first, fail closed".

## Decision
1. **Code can merge, runtime stays separate.** pios-algo may later move into the PIOS repo as a module (`git subtree` keeps history) and share PIOS's event store and core. The **engine and the watchdog always run as their own processes**, so a PIOS outage can never block an exit, and the watchdog never runs on the box it watches.
2. **Rules that keep the brick merge-ready** (enforced by `tests/test_boundaries.py` where possible):
   - No imports from outside the package except stdlib and allow-listed libraries (today: `pydantic`). No PIOS imports, no tenant strategy code.
   - Every event type is namespaced `algo.*`; every SQL object is prefixed `algo_`, so it can share a database with PIOS without clashes.
   - Own schema migrations (`algo_schema_migrations`); never edits PIOS tables.
   - All configuration injected (paths, tenant, keys via ports) — no globals, no module-level state.
   - Storage behind the `EventStore` port (PIOS ADR-012), upcasting at the repo layer (ADR-013), projectors with position tracking (ADR-014).
   - Talks to the outside only through ports + the published contracts: `schemas/event-envelope.v1.json` and the FastAPI/OpenAPI spec.
3. **Never merges:** `will-strategies` and broker keys stay the tenant's (ADR-002 A1, A4, A7).

## Consequences
- + Merging later = move the folder, swap the store adapter; no rewrite.
- + One codebase / auth / audit once merged; trading still isolated at runtime.
- − Prefixes and the import rule add small friction now.
- If PIOS adopts a different envelope, the upcaster handles it (ADR-013) — the `algo.` namespace keeps both readable side by side.
