"""Events: envelope v1, append-only store port, SQLite store, legacy upcaster."""

from pios_algo.events.envelope import ENVELOPE_VERSION, Envelope, EventType, Meta, export_json_schema
from pios_algo.events.sqlite_store import SqliteEventStore
from pios_algo.events.store import (
    AppendResult,
    ConcurrencyError,
    DuplicateEventConflict,
    EventStore,
    StoredEvent,
    TenantMismatch,
    UnknownEventVersion,
)

__all__ = [
    "ENVELOPE_VERSION",
    "AppendResult",
    "ConcurrencyError",
    "DuplicateEventConflict",
    "Envelope",
    "EventStore",
    "EventType",
    "Meta",
    "SqliteEventStore",
    "StoredEvent",
    "TenantMismatch",
    "UnknownEventVersion",
    "export_json_schema",
]
