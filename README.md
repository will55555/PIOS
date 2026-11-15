# PIOS

Personal Investment Operating System: Terra Finance's event-sourced capital governance engine. It records why capital moved, computes against user-set parameters, and authorizes governed orders. It never places them itself: the `pios/algo` execution subsystem does, only inside PIOS authorization (ADR-022, read with ADR-016).

**Status: scaffold only.** The learning gate is still open, so this repo holds the skeleton, interfaces and stubs, with no features (ADR-020). Design lives in [Notion](https://app.notion.com/p/36f89370d4978140a5a9d14f76ddaefd); decisions are in [docs/adr](docs/adr/README.md).

## How it bridges Finance

PIOS is the engine behind the strategies in the Notion Finance space. Each strategy becomes a policy template here: rule shape and parameter names only (ADR-016). Will's values stay on the Finance pages as parameter sets. [Doc 24, the Finance Strategy → PIOS map](https://app.notion.com/p/3fc89370d497814180aada37d64ff686), lists every template, its events and where its values live. A new Finance strategy gets a row there first.

Domains such as liabilities, consumer capital and travel arrive as feature modules on top of the six layers, each with its own migrations folder. Travel has no ADR yet (PIOS-008).

## Stack

Python 3.15 · FastAPI · SQLite (dev) → PostgreSQL (prod, schema-level multi-tenant) · pytest, ruff, mypy strict

PIOS is a multi-language repo by design: each component uses its best-fit language from the start (ADR-PIOS-ALGO-009 amendment, 2026-11-14). Only the Python Core exists today.

| Component | Language | Status |
| --- | --- | --- |
| PIOS Core (events, projections, policy, allocation), ingestion adapters | Python (FastAPI) | Scaffold |
| `pios/algo` engine, broker adapters, strategies, market-data gateway, watchdog, Lambdas | Python | In build in the pios-algo repo |
| Backtest/sweep engine, scanner, indicator library, Monte Carlo, options pricing | C++ (pybind11), compute only | Indicator library at `pios/algo/compute`; the rest not started |
| UI and analysis workstation (ADR-018, ADR-PIOS-ALGO-019) | TypeScript (Angular) | Separate `pios-fe` repo, same model as terra-api-fe (served same-origin by Core); app not generated yet |
| Terra API and integration services | Java (Spring Boot) | Lives in `terra-api` |
| Storage and analytics | SQL (SQLite → PostgreSQL) | Stubs in `migrations/` |
| Cross-language contracts | JSON Schema / OpenAPI | [`contracts/`](contracts/README.md); the envelope schema stays in `pios/algo/schemas/` until cutover |
| Infrastructure | Terraform | `pios/algo/infra/terraform` |
| TradingView studies and alerts | Pine Script | Private, in `will-strategies/pine` |

C++ computes and Python decides: native code never owns policy, authorization, broker connectivity, order state or financial truth.

Every module builds, tests, lints and runs through one entry point: `bash scripts/task.sh <core|algo|compute> <build|test|lint|run>`. CI still calls `scripts/check.sh`.

## Layout

One package per schema layer, plus the persistence boundary and API:

| Path | Holds |
| --- | --- |
| `pios/events` | Layer 1: envelope, upcaster chain |
| `pios/projections` | Layer 2: projector port |
| `pios/snapshots` | Layer 3: interface only (ADR-014) |
| `pios/tenancy` | Layer 4: tenant ids and schema names |
| `pios/correlation` | Layer 5: correlation and causation chain |
| `pios/risk_control` | Layer 6: empty until the gate clears |
| `pios/repositories` | The abstract interface, SQLite and PostgreSQL stubs, migration discovery (ADR-012) |
| `pios/api` | FastAPI app factory, no routes |
| `migrations/` | Modular, one folder per module ([details](migrations/README.md)) |
| `pios/algo` | pios-algo, imported with history by `git subtree` (2026-11-05, `d11d951`). Separately built and deployed. Change it in the pios-algo repo, not here |

## Run the checks

Needs Python 3.15. With [uv](https://docs.astral.sh/uv/):

```bash
uv self update
uv python install 3.15
uv venv --python 3.15
source .venv/Scripts/activate
uv pip install -e ".[dev]"
bash scripts/check.sh
```

GitHub Actions and the Jenkinsfile both call `scripts/check.sh`. The Jenkinsfile stays dormant until a job exists on the shared box.

## How pios-algo joined

Imported 2026-11-05 under the [Repository Consolidation Protocol](https://app.notion.com/p/40d89370d497812488bcc0e871533510), pios-algo `main` at `b907f2d` → PIOS `main` at `d11d951`. To bring in later pios-algo changes:

```bash
git subtree pull --prefix=pios/algo pios-algo main   # until the standalone repo is retired
```

The standalone pios-algo repo stays canonical until the protocol's acceptance gate passes and Will records the cutover. The rules that must survive it are in [ADR-020](docs/adr/ADR-020-event-core-and-algo-boundary.md) and ADR-022. `will-strategies` and broker keys never join.

## Remote

GitHub `will55555/pios` (`origin`). The `pios-algo` remote points at `will55555/pios-algo` for subtree pulls. Bitbucket `terra-inc-dev/*` remains as the `bitbucket` remote, no longer pushed.
