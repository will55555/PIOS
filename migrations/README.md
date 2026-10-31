# Migrations

Modular, and empty for now. Each module owns its own folder and numbers its own files:

```
migrations/<module>/<sqlite|postgres>/NNNN_name.sql
```

- **Adding a module is adding a folder.** `pios.repositories.migrations.discover` finds it. A misnamed file is an error, not a skip.
- **Baselines are comment-only.** The design names a 14-table, 6-layer schema (`pios_schema_v1.0.0`), but no table-level DDL was found in Notion, the Obsidian vault or SDE (searched 2026-10-31). Tables get written with the feature that needs them, in that feature's module, and not before the learning gate clears (ADR-020).
- **Both dialects, always.** A change ships for SQLite and PostgreSQL together (ADR-012).
- **PIOS tracks** applied files by `(module, version)` in `pios_schema_migrations`, once a runner exists. No runner yet: nothing to apply.
- **Algo keeps its own.** pios-algo has its own `algo_` tables and `algo_schema_migrations`. It never edits PIOS tables, and PIOS never edits its tables (algo ADR-003).
