"""SQLite EventStore — one database file per tenant (build step 1 brief §5)."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Sequence
from pathlib import Path

from pios_algo.events.envelope import Envelope
from pios_algo.events.store import (
    AppendResult,
    ConcurrencyError,
    DuplicateEventConflict,
    EventStore,
    EventStoreError,
    StoredEvent,
    TenantMismatch,
)
from pios_algo.tenancy import tenant_dir, validate_tenant_id

# All objects are prefixed ``algo_`` so this module can share a database with PIOS (ADR-003).
SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS algo_schema_migrations (
    version    INTEGER PRIMARY KEY,
    applied_at TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
INSERT OR IGNORE INTO algo_schema_migrations (version) VALUES (1);
CREATE TABLE IF NOT EXISTS algo_events (
    global_seq     INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id       TEXT    NOT NULL UNIQUE,
    stream_id      TEXT    NOT NULL,
    stream_version INTEGER NOT NULL,
    type           TEXT    NOT NULL,
    ts             TEXT    NOT NULL,
    body           TEXT    NOT NULL,
    UNIQUE (stream_id, stream_version)
);
CREATE INDEX IF NOT EXISTS ix_algo_events_stream ON algo_events (stream_id, stream_version);
CREATE TRIGGER IF NOT EXISTS algo_events_no_update BEFORE UPDATE ON algo_events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS algo_events_no_delete BEFORE DELETE ON algo_events
BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
"""


def _canonical(env: Envelope) -> str:
    return json.dumps(json.loads(env.to_json()), sort_keys=True, separators=(",", ":"))


class SqliteEventStore(EventStore):
    """Store bound to exactly one tenant: ``<root>/tenants/<tenant_id>/events.db``."""

    def __init__(self, root: Path | str, tenant_id: str) -> None:
        self.tenant_id = validate_tenant_id(tenant_id)
        directory = tenant_dir(Path(root), tenant_id)
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / "events.db"
        self._conn = sqlite3.connect(self.path, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> SqliteEventStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- helpers ---------------------------------------------------------
    def _check_tenant(self, tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise TenantMismatch(f"store is for tenant {self.tenant_id!r}, got {tenant_id!r}")

    def stream_version(self, tenant_id: str, stream_id: str) -> int:
        self._check_tenant(tenant_id)
        row = self._conn.execute(
            "SELECT COALESCE(MAX(stream_version), 0) FROM algo_events WHERE stream_id = ?", (stream_id,)
        ).fetchone()
        return int(row[0])

    # -- port ------------------------------------------------------------
    def append(self, events: Sequence[Envelope], expected_version: int | None = None) -> AppendResult:
        if not events:
            return AppendResult(0, 0, None)
        for e in events:
            self._check_tenant(e.tenant_id)
        if expected_version is not None and len({e.stream_id for e in events}) != 1:
            raise EventStoreError("expected_version requires all events in one stream")

        appended = skipped = 0
        last_seq: int | None = None
        cur = self._conn.cursor()
        cur.execute("BEGIN IMMEDIATE")
        try:
            if expected_version is not None:
                current = self.stream_version(self.tenant_id, events[0].stream_id)
                if current != expected_version:
                    raise ConcurrencyError(
                        f"stream {events[0].stream_id!r} at version {current}, expected {expected_version}"
                    )
            for e in events:
                body = _canonical(e)
                existing = cur.execute("SELECT body FROM algo_events WHERE event_id = ?", (str(e.event_id),)).fetchone()
                if existing is not None:
                    if existing[0] != body:
                        raise DuplicateEventConflict(f"event {e.event_id} already stored with different content")
                    skipped += 1
                    continue
                version = int(
                    cur.execute(
                        "SELECT COALESCE(MAX(stream_version), 0) FROM algo_events WHERE stream_id = ?", (e.stream_id,)
                    ).fetchone()[0]
                ) + 1
                cur.execute(
                    "INSERT INTO algo_events (event_id, stream_id, stream_version, type, ts, body) "
                    "VALUES (?,?,?,?,?,?)",
                    (str(e.event_id), e.stream_id, version, e.type.value, e.ts.isoformat(), body),
                )
                last_seq = cur.lastrowid
                appended += 1
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
        return AppendResult(appended, skipped, last_seq)

    def _rows(self, sql: str, args: tuple[object, ...]) -> Iterator[StoredEvent]:
        for seq, version, body in self._conn.execute(sql, args):
            yield StoredEvent(seq, version, Envelope.from_json(body))

    def read_stream(self, tenant_id: str, stream_id: str) -> list[StoredEvent]:
        self._check_tenant(tenant_id)
        return list(
            self._rows(
                "SELECT global_seq, stream_version, body FROM algo_events WHERE stream_id = ? ORDER BY stream_version",
                (stream_id,),
            )
        )

    def read_all(self, tenant_id: str, since: int | None = None) -> list[StoredEvent]:
        self._check_tenant(tenant_id)
        return list(
            self._rows(
                "SELECT global_seq, stream_version, body FROM algo_events WHERE global_seq > ? ORDER BY global_seq",
                (since or 0,),
            )
        )

    def count(self) -> int:
        return int(self._conn.execute("SELECT COUNT(*) FROM algo_events").fetchone()[0])
