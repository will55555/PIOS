# PIOS Tasks

| ID | Task | Status | Context |
| --- | --- | --- | --- |
| PIOS-001 | Scaffold the repo | Done | 2026-10-31. Will ran the checks on Python 3.15.2: 25 tests passed, ruff and mypy strict clean. Scope and decisions: ADR-020. |
| PIOS-002 | Design the tables for each schema layer | Blocked | No DDL for `pios_schema_v1.0.0` was found. Rebuild module by module from the layer summary and ADRs 016, 017, 019. Blocked on the learning gate. |
| PIOS-003 | Add ADR-020 to the PIOS Notion page | Open | Written in this repo first. |
| PIOS-004 | Pick the remote with pios-algo | Open | The Terra GitHub org does not exist yet. |
| PIOS-005 | Bring in pios-algo by subtree | Later | After PIOS has a skeleton worth joining and step 2 is pulled. Does not hold up algo steps 3–9. |
| PIOS-006 | Create the Jenkins job | Later | The Jenkinsfile is dormant until then. |
| PIOS-007 | Build the algo event translator | Blocked | Designed in ADR-020. Blocked on the learning gate. |
| PIOS-008 | Write the travel layer ADR (next free number, 021) | Open | Design work, so the gate doesn't block it. Motivating case: Trip ↔ Expense sync, open item https://app.notion.com/p/3da89370d4978198ab71cef2ad7aa37c. Also add a row to doc 24 and link the item from the PIOS page: it sits under Terra Inc / Tech, so it's easy to miss. |
