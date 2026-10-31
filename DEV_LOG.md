# PIOS Dev Log

## Scaffold
**Date:** 2026-10-31  **Status:** Complete. Will ran `scripts/check.sh` on Python 3.15.2: 25 tests passed, ruff and mypy strict clean (15 source files; mypy 2.4.1, ruff 0.17.3, pytest 9.2.0).

### Goal
Give pios-algo a repo to join later without slowing the algo build.

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
