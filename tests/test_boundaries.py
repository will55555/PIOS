"""ADR-003 merge-ready brick: enforce the package boundary in CI."""

from __future__ import annotations

import ast
import sqlite3
import sys
from pathlib import Path

from pios_algo.events import EventType, SqliteEventStore

PKG = Path(__file__).resolve().parents[1] / "src" / "pios_algo"
ALLOWED_THIRD_PARTY = {"pydantic"}
STDLIB = set(sys.stdlib_module_names)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def test_no_imports_outside_package():
    """Only stdlib, pios_algo itself and the allow-listed libraries — no PIOS, no tenant strategy code."""
    offenders = {}
    for py in PKG.rglob("*.py"):
        bad = _imports(py) - STDLIB - ALLOWED_THIRD_PARTY - {"pios_algo", "__future__"}
        if bad:
            offenders[str(py.relative_to(PKG))] = sorted(bad)
    assert offenders == {}


def test_event_types_are_namespaced():
    assert all(t.value.startswith("algo.") for t in EventType)


def test_sql_objects_are_prefixed(tmp_path):
    with SqliteEventStore(tmp_path, "will") as s:
        names = [r[0] for r in sqlite3.connect(s.path).execute(
            "SELECT name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")]
        versions = [r[0] for r in sqlite3.connect(s.path).execute("SELECT version FROM algo_schema_migrations")]
    assert names and all(n.startswith(("algo_", "ix_algo_")) for n in names)
    assert versions == [1]
