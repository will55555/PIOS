"""The skeleton holds together: stubs honour the interface, the app wires a repository, migrations stay modular."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from pios.api import create_app
from pios.events import UpcasterRegistry
from pios.repositories import PostgresRepository, Repository, SqliteRepository
from pios.repositories.migrations import discover

ROOT = Path(__file__).resolve().parents[1]
LAYERS = {"events", "projections", "snapshots", "tenancy", "correlation", "risk_control"}


@pytest.fixture(params=["sqlite", "postgres"])
def repository(request, tmp_path) -> Repository:
    if request.param == "sqlite":
        return SqliteRepository(tmp_path, UpcasterRegistry())
    return PostgresRepository("postgresql://unused", UpcasterRegistry())


def test_repository_stubs_refuse_to_pretend(repository):
    with pytest.raises(NotImplementedError):
        asyncio.run(repository.get_latest_position("will"))


def test_app_factory_injects_the_repository(repository):
    app = create_app(repository)
    assert app.state.repository is repository


@pytest.mark.parametrize("dialect", ["sqlite", "postgres"])
def test_every_layer_has_an_empty_baseline(dialect):
    found = discover(ROOT / "migrations", dialect)
    assert {m.module for m in found} == LAYERS
    assert all(m.version == 1 for m in found)
    for migration in found:
        lines = migration.path.read_text(encoding="utf-8").splitlines()
        assert all(line.startswith("--") or not line.strip() for line in lines), migration.path


def test_new_module_is_just_a_new_folder(tmp_path):
    folder = tmp_path / "liabilities" / "sqlite"
    folder.mkdir(parents=True)
    (folder / "0002_more.sql").write_text("-- second", encoding="utf-8")
    (folder / "0001_first.sql").write_text("-- first", encoding="utf-8")
    assert [(m.module, m.version) for m in discover(tmp_path, "sqlite")] == [("liabilities", 1), ("liabilities", 2)]


def test_misnamed_migration_is_an_error(tmp_path):
    folder = tmp_path / "events" / "sqlite"
    folder.mkdir(parents=True)
    (folder / "first.sql").write_text("-- bad", encoding="utf-8")
    with pytest.raises(ValueError):
        discover(tmp_path, "sqlite")
