"""ADR-012 and ADR-020 boundaries, enforced in CI."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "pios"
ALLOWED_THIRD_PARTY = {"fastapi", "pydantic"}
STDLIB = set(sys.stdlib_module_names)
SQL_RE = re.compile(r"\b(INSERT\s+INTO|CREATE\s+TABLE|DELETE\s+FROM|SELECT\s+.+\s+FROM)\b", re.IGNORECASE)


def _sources() -> list[Path]:
    """All PIOS code. pios/algo is excluded: it arrives by subtree and has its own boundary test."""
    return [p for p in PKG.rglob("*.py") if "algo" not in p.relative_to(PKG).parts]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_only_allowed_imports():
    offenders = {}
    for py in _sources():
        tops = {name.split(".")[0] for name in _imports(py)}
        bad = tops - STDLIB - ALLOWED_THIRD_PARTY - {"pios", "__future__"}
        if bad:
            offenders[str(py.relative_to(PKG))] = sorted(bad)
    assert offenders == {}


def test_pios_never_imports_algo():
    """PIOS reads algo only through schemas/event-envelope.v1.json and its OpenAPI spec (algo ADR-003, ADR-020)."""
    offenders = {}
    for py in _sources():
        bad = {n for n in _imports(py) if n.startswith(("pios_algo", "pios.algo", "will_strategies"))}
        if bad:
            offenders[str(py.relative_to(PKG))] = sorted(bad)
    assert offenders == {}


def test_sql_lives_only_in_repositories():
    offenders = []
    for py in _sources():
        if "repositories" in py.relative_to(PKG).parts:
            continue
        if SQL_RE.search(py.read_text(encoding="utf-8")):
            offenders.append(str(py.relative_to(PKG)))
    assert offenders == []


def test_one_package_per_schema_layer():
    for layer in ("events", "projections", "snapshots", "tenancy", "correlation", "risk_control"):
        assert (PKG / layer / "__init__.py").is_file(), layer
