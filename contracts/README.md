# contracts

Cross-language contracts for the PIOS repo (ADR-PIOS-ALGO-009, -017; PIOS ADR-020, -022): JSON Schema and OpenAPI, Protobuf only if needed.

## Rules

- Languages talk only through contracts in this folder. Each language generates its types from here; there are no direct cross-language imports.
- Python (Core and algo) and C++ (`pios/algo/compute`) generate from these files; the separate `pios-fe` repo generates its TypeScript client from the published OpenAPI spec.
- CI will fail on stale generated code (not wired yet).

## Current state

`event-envelope.v1.json` still lives in `pios/algo/schemas/`, owned by the pios-algo repo. It moves here only after the Repository Consolidation Protocol cutover is recorded.
