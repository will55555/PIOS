from __future__ import annotations

import sqlite3

import pytest

from pios_algo.events import ConcurrencyError, DuplicateEventConflict, SqliteEventStore, TenantMismatch
from pios_algo.tenancy import InvalidTenantId


@pytest.fixture
def store(tmp_path):
    s = SqliteEventStore(tmp_path, "will")
    yield s
    s.close()


def test_append_and_read(store, make_event):
    a, b = make_event(), make_event(payload={"n": 2})
    r = store.append([a, b])
    assert (r.appended, r.skipped_duplicates) == (2, 0)
    got = store.read_stream("will", a.stream_id)
    assert [g.envelope for g in got] == [a, b]
    assert [g.stream_version for g in got] == [1, 2]
    assert [g.envelope for g in store.read_all("will", since=got[0].global_seq)] == [b]


def test_db_file_is_per_tenant(tmp_path):
    with SqliteEventStore(tmp_path, "will") as s:
        assert s.path == tmp_path / "tenants" / "will" / "events.db"


def test_idempotent_reappend(store, make_event):
    e = make_event()
    store.append([e])
    r = store.append([e])
    assert (r.appended, r.skipped_duplicates) == (0, 1)
    assert store.count() == 1


def test_same_id_different_content_conflicts(store, make_event):
    e = make_event()
    store.append([e])
    with pytest.raises(DuplicateEventConflict):
        store.append([make_event(event_id=e.event_id, payload={"other": 1})])


def test_optimistic_concurrency(store, make_event):
    sid = make_event().stream_id
    store.append([make_event()], expected_version=0)
    with pytest.raises(ConcurrencyError):
        store.append([make_event()], expected_version=0)
    store.append([make_event()], expected_version=1)
    assert store.stream_version("will", sid) == 2


def test_failed_batch_is_atomic(store, make_event):
    e = make_event()
    store.append([e])
    with pytest.raises(DuplicateEventConflict):
        store.append([make_event(payload={"n": 9}), make_event(event_id=e.event_id, payload={"x": 1})])
    assert store.count() == 1


def test_tenant_isolation(tmp_path, make_event):
    with SqliteEventStore(tmp_path, "will") as will, SqliteEventStore(tmp_path, "tenant-2") as other:
        with pytest.raises(TenantMismatch):
            will.append([make_event(tenant_id="tenant-2")])
        with pytest.raises(TenantMismatch):
            will.read_all("tenant-2")
        other.append([make_event(tenant_id="tenant-2")])
        assert will.count() == 0 and other.count() == 1


def test_bad_tenant_cannot_escape_root(tmp_path):
    with pytest.raises(InvalidTenantId):
        SqliteEventStore(tmp_path, "../evil")


def test_rows_cannot_be_updated_or_deleted(store, make_event):
    store.append([make_event()])
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        store._conn.execute("UPDATE algo_events SET type = 'x'")
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        store._conn.execute("DELETE FROM algo_events")
