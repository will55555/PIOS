# PIOS Tasks

| ID | Task | Status | Context |
| --- | --- | --- | --- |
| PIOS-001 | Scaffold the repo | Done | 2026-10-31. Will ran the checks on Python 3.15.2: 25 tests passed, ruff and mypy strict clean. Scope and decisions: ADR-020. |
| PIOS-002 | Design the tables for each schema layer | Blocked | No DDL for `pios_schema_v1.0.0` was found. Rebuild module by module from the layer summary and ADRs 016, 017, 019. Blocked on the learning gate. |
| PIOS-003 | Add ADR-020 to the PIOS Notion page | Done | 2026-10-31, as a child page of PIOS. |
| PIOS-004 | Pick the remote with pios-algo | Done | 2026-11-05: Bitbucket `terra-inc-dev/pios` and `terra-inc-dev/pios-algo`. Moved to GitHub `will55555/pios` and `will55555/pios-algo` 2026-11-15; Bitbucket kept as `bitbucket`, not pushed. |
| PIOS-005 | Bring in pios-algo by subtree | Done (gate open) | 2026-11-05: imported at `pios/algo`, `d11d951`, history kept, secret scans clean. The Consolidation Protocol §9 acceptance gate and cutover are still open. |
| PIOS-006 | Create the Jenkins job | Later | The Jenkinsfile is dormant until then. |
| PIOS-007 | Build the algo event translator | Blocked | Designed in ADR-020. Blocked on the learning gate. |
| PIOS-008 | Write the travel layer ADR (next free number, 021) | Open | Design work, so the gate doesn't block it. Motivating case: Trip ↔ Expense sync, open item https://app.notion.com/p/3da89370d4978198ab71cef2ad7aa37c. Also add a row to doc 24 and link the item from the PIOS page: it sits under Terra Inc / Tech, so it's easy to miss. |
