# PIOS ADR-018: Frontend Framework — Angular Over React/Next.js

> Copied 2026-10-31 from Notion: https://app.notion.com/p/3c689370d49781e880a0d7283812214d

> Renumbered 2026-10-23 (Will approved): formerly titled "16 — Frontend Framework…". The number 16 collided with doc "16 — Amendment, Versioning & Long-Term Stewardship" and with PIOS ADR-016 (Parameterized Policy Engine). Now **PIOS ADR-018** in the local PIOS ADR sequence. Decision unchanged.

*(Frontend Architecture Decision)*

## Status

Accepted

## Context

The original SDE scoping conversation (pre-dating the current design doc series) recommended **React/Next.js** for the frontend and explicitly rejected Angular, citing complexity and rigidity. That recommendation was made before PIOS's governance-first architecture (event sourcing, strict domain modeling, rules-engine gating, immutable DecisionRecords) was fully specified.

Current PIOS design docs (Vision & Core Design Documentation, Architecture Decision Records) and the accepted learning sequence (Python → **Angular** → DSA → coding) both assume Angular as the frontend framework. This had never been captured as a formal ADR — it existed only as an informal open item.

## Why React Was Originally Recommended

The early recommendation weighed React/Next.js as a **thin, backend-driven UI** — minimal framework overhead, fast to prototype, flexible component composition, large ecosystem, and less structural ceremony for a single-developer project. Angular was passed over at that stage specifically because of its opinionated structure, steeper learning curve (RxJS, DI, modules), and more boilerplate — reasonable concerns for a lightweight app, but that assessment was made before the system's actual shape was known.

## Why Angular Fits PIOS Better

PIOS is not a lightweight app — it's a governance engine with:

- **Strict typed domain models** (CapitalUnit, CapitalBucket, Strategy, Rule, Signal, DecisionRecord, RiskBudget) that map cleanly onto Angular's TypeScript-first, strongly-typed architecture
- **Read-heavy, write-restricted API design** (ADR-008) — Angular's structured module/service/DI pattern enforces the same discipline on the frontend that the backend enforces on capital actions, rather than leaving data-fetching patterns ad hoc
- **Long-lived, single-maintainer codebase** — Angular's opinionated conventions reduce architectural drift over years of solo development, where React's flexibility can accumulate inconsistent patterns without a team to enforce norms
- **GraphQL integration** (Strawberry GraphQL, hybrid GraphQL/REST) — Angular's Apollo Angular tooling is mature and integrates predictably with strongly-typed schemas
- **Governance-over-optimization philosophy** (Principle 6, ADR-010: Safety Over Performance) — Angular's rigidity is a feature here, not a bug; it mirrors the system's own preference for enforced structure over flexible convenience

In short: the complexity that made Angular a poor fit for a generic app is the same structure that makes it a good fit for a governance system that explicitly values explainability, consistency, and resistance to silent drift over developer speed.

## Decision

PIOS frontend SHALL be built in **Angular**, not React/Next.js. This formally supersedes the informal React recommendation from the original SDE scoping conversation.

## Consequences

- Learning sequence (Python → Angular → DSA → coding) is confirmed correct and requires no adjustment
- Frontend component design (a remaining design gap) should proceed with Angular module/service conventions in mind
- Any future frontend tooling decisions (state management, GraphQL client, component libraries) should be evaluated within the Angular ecosystem

---

**Date:** 2026-08-24

**Status:** Accepted

**Owner:** System Architect (User)
