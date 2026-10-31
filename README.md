# PIOS

Personal Investment Operating System: Terra Finance's event-sourced capital governance engine. It records why capital moved, computes against user-set parameters, and recommends. It does not place orders (ADR-001, ADR-016).

**Status: scaffold only.** The learning gate is still open, so this repo holds the skeleton, interfaces and stubs, with no features (ADR-020). Design lives in [Notion](https://app.notion.com/p/36f89370d4978140a5a9d14f76ddaefd); decisions are in [docs/adr](docs/adr/README.md).

## How it bridges Finance

PIOS is the engine behind the strategies in the Notion Finance space. Each strategy becomes a policy template here: rule shape and parameter names only (ADR-016). Will's values stay on the Finance pages as parameter sets. [Doc 24, the Finance Strategy → PIOS map](https://app.notion.com/p/3fc89370d497814180aada37d64ff686), lists every template, its events and where its values live. A new Finance strategy gets a row there first.

Domains such as liabilities, consumer capital and travel arrive as feature modules on top of the six layers, each with its own migrations folder. Travel has no ADR yet (PIOS-008).

## Stack

Python 3.15 · FastAPI · SQLite (dev) → PostgreSQL (prod, schema-level multi-tenant) · pytest, ruff, mypy strict

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
| `pios/algo` | Not here yet: pios-algo joins by `git subtree` |

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

## How pios-algo joins

Only once this skeleton is worth joining. The algo build does not wait for PIOS.

```bash
git subtree add --prefix=pios/algo ../pios-algo main
git subtree pull --prefix=pios/algo ../pios-algo main   # until the standalone repo is retired
```

This keeps history and avoids two diverging copies. The rules that must survive it are in [ADR-020](docs/adr/ADR-020-event-core-and-algo-boundary.md). `will-strategies` and broker keys never join.

## Remote

Local only for now. The Terra GitHub org does not exist yet; its home gets decided together with pios-algo's.
