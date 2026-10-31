# PIOS

Engineering Hub project, task prefix `PIOS`. Load the hub first: `claude-skills/skills/ai-control/HUB.md`, then the PIOS section of `HUB_STATE.md`.

- **Scaffold only.** The learning gate is open: no event types, projectors, rules engine, routes or tables until Will clears or lifts it (ADR-020).
- **Read `docs/adr` before designing.** Code changes reference the ADR IDs they apply.
- **Boundaries:** no SQL outside `pios/repositories`; no imports of `pios_algo` or `will_strategies`; no tenant data, keys or personal financial values in this repo.
- **pios/algo is a subtree.** Change it in the pios-algo repo, not here.
- **Will runs the checks:** `bash scripts/check.sh`.
