# PIOS Dev Log

## Scaffold
**Date:** 2026-10-31  **Status:** Complete. Will ran `scripts/check.sh` on Python 3.15.2: 25 tests passed, ruff and mypy strict clean (15 source files; mypy 2.4.1, ruff 0.17.3, pytest 9.2.0).

### Goal
Give pios-algo a repo to join later without slowing the algo build.

First commit: `050ecc5`. To reproduce the checks, follow "Run the checks" in `README.md`; `uv self update` comes first, because the older uv only offered the 3.15 beta.

### Decisions (Will)
- Learning gate stays, so scaffold only.
- PIOS owns its envelope; algo events cross through a translator. See ADR-020 for why `pios_algo.events` could not be adopted.
- CI is both GitHub Actions and a dormant Jenkinsfile, sharing `scripts/check.sh`.
- Local only; the remote gets decided together with pios-algo's.
- Python 3.15 for PIOS, replacing the 3.10 in the seed prompt.
- Migrations are an empty, modular baseline.

### Departures from the seed prompt
- New ADR is 020, not 015: ADRs 015–019 already exist.
- ADRs 001–019 are copied in, not 001–014.
- ADR-019 is an edited copy: personal accounts, debts and baselines stay in Notion.

### Sources
PIOS Notion page and ADRs; Obsidian `Knowledge/Projects/PIOS` (the 6-layer summary); `pios-algo/docs` and `pios-algo/src/pios_algo/events`. No table-level DDL exists in any of them. Algo ADR-002 and the seed prompt file were not available locally, so their content comes from the planning notes and the prompt as pasted.

### Travel layer
Will spotted it missing from the plan. It exists only as a Notion open item (2026-09-13) under Terra Inc / Tech, not under the PIOS page, and has no row in doc 24. Tracked as PIOS-008. Likely shape, to be decided in that ADR: expense events carry the trip ID, and both the trip summary and the expense list are projections, so there is only one write and nothing to keep in sync.

### Known limitations
- Only checked on Windows so far. Neither CI pipeline has run: there is no remote yet, and the Jenkinsfile has no job.
- `aiosqlite` and `asyncpg` are not dependencies yet: the stubs import no driver. Both have Python 3.15 support on PyPI (checked 2026-10-31).

## Language scaffold and pios-fe split
**Date:** 2026-11-14 to 2026-11-15  **Status:** Written, uncommitted. No PIOS code changed, so `scripts/check.sh` was not rerun.

### Goal
Close the drift between Notion, the repos and the hub after Will's ADR changes, and apply the ADR-PIOS-ALGO-009 amendment: each component uses its best-fit language from the start.

### Changes
- `README.md`: language table (Python Core and algo, C++ compute in `pios/algo/compute`, Angular UI in the separate `pios-fe` repo, Java in `terra-api`, SQL, JSON Schema/OpenAPI, Terraform at `pios/algo/infra/terraform`, Pine in `will-strategies/pine`), the rule "C++ computes, Python decides", the ADR-022 intro wording (PIOS authorizes, `pios/algo` executes), updated subtree and remote sections.
- `scripts/task.sh`: one entry point, `bash scripts/task.sh <core|algo|compute> <build|test|lint|run>`; anything not wired yet exits 2. CI still calls `scripts/check.sh`.
- `contracts/README.md`: new. Languages meet only through contracts; the envelope schema stays in `pios/algo/schemas/` until the consolidation cutover; `pios-fe` generates its TypeScript client from the published OpenAPI spec.
- `docs/adr/README.md`: rows for 021 (reserved, travel) and 022, and a note on the ADR-PIOS-ALGO series. `ADR-016`: cross-reference to ADR-022.
- `TASKS.md`: PIOS-004 Done (Bitbucket), PIOS-005 Done with the §9 acceptance gate still open.

### Decisions (Will)
- The UI gets its own repo, `pios-fe`, the same model as terra-api-fe: built by Core's pipeline and served same-origin by FastAPI. A `frontend/` folder created earlier this session was removed (never committed). Rejected: keeping the UI inside the Python repo, which mixes the Node toolchain into Core's CI.
- From 2026-11-15 Will drives: he sets up, builds, runs and commits; Claude reviews and writes only on approval.

### Known limitations / next
- `pios/algo/compute` only arrives with the next subtree pull, after pios-algo is pushed.
- CI is GitHub Actions on a Bitbucket repo, so it cannot run. Decision pending (Pipelines vs check script).
- `pios-fe` has no git or remote yet; the Angular app is not generated.

## Moved to GitHub
**Date:** 2026-11-15  **Status:** Pushed (`main` `4ca9cf5`).

- `origin` → `https://github.com/will55555/pios.git` (private); the `pios-algo` subtree remote → `https://github.com/will55555/pios-algo.git`; Bitbucket kept as `bitbucket`, no longer pushed. History and the subtree link are unchanged: only URLs moved.
- Why: the existing `.github/workflows/ci.yml` (ubuntu, `scripts/check.sh`) could not run on Bitbucket. It now runs on every push. It tests only `tests/` (pytest `testpaths`); `pios/algo` is tested by pios-algo's own workflow, so nothing runs twice.
- README Remote section, TASKS PIOS-004 and the Consolidation Protocol hosting note updated. The 2026-11-05 execution record keeps its Bitbucket URLs as history.
