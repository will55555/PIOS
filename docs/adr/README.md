# PIOS ADRs

Notion is the source for ADRs 001–019: https://app.notion.com/p/36f89370d4978140a5a9d14f76ddaefd. ADR-020 started here and is mirrored there. Accepted ADRs are immutable; a change needs a new ADR.

| ADR | Decision | Status |
| --- | --- | --- |
| [001–010](ADR-001-010-governance.md) | Governance: capital governance engine, firewalls, immutable intent, risk budgets, AI advisory-only, rules engine, decision records, read-heavy API, paper first, safety over performance | Accepted |
| [011](ADR-011-event-sourced-write-path.md) | Event-sourced write path, projection read path | Accepted |
| [012](ADR-012-repository-pattern.md) | Repository pattern, SQLite dev and PostgreSQL prod | Accepted |
| [013](ADR-013-event-schema-versioning.md) | Upcasting at the repository layer, hard error on unknown versions | Accepted |
| [014](ADR-014-projection-rebuild-strategy.md) | Manual rebuilds, per-projector positions, snapshots designed not built | Accepted |
| [015](ADR-015-consumer-capital-layer.md) | Consumer capital layer | Accepted (design-level) |
| [016](ADR-016-parameterized-policy-engine.md) | Parameterized policy engine, no hard-coded financial values | Proposed |
| [017](ADR-017-liabilities-and-mode-gate.md) | Liabilities and the Repair ↔ Growth mode gate | Proposed |
| [018](ADR-018-frontend-angular.md) | Angular frontend | Accepted |
| [019](ADR-019-ingestion-adapters.md) | Ingestion adapters, observed vs derived reconciliation (edited copy) | Proposed |
| [020](ADR-020-event-core-and-algo-boundary.md) | PIOS owns its envelope; pios-algo boundary; scaffold-only; Python 3.15 | Accepted |
| 021 | Reserved: travel layer (PIOS-008) | Not written |
| [022](https://app.notion.com/p/40d89370d49781ac9d98fc0659eeb0f5) | Modular-monolith Core plus independently deployed algo execution service; PIOS authorizes, algo executes (Notion only) | Accepted 2026-11-03 |

The algo subsystem has its own series, ADR-PIOS-ALGO-001–019, mapped in the [pios-algo Architecture Baseline](https://app.notion.com/p/40c89370d49781d7ac0dd8f959a7cb65) §14. ALGO-009 (amended 2026-11-14) sets the language per component; ALGO-019 puts all UI in PIOS.
