"""EventStore port (append-only). Implementations: SQLite now, Postgres later (PIOS ADR-012)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pios_algo.events.envelope import Envelope


class EventStoreError(Exception):
    pass


class ConcurrencyError(EventStoreError):
    """The stream moved on since the caller read it (optimistic concurrency)."""


class DuplicateEventConflict(EventStoreError):
    """Same event_id appended again with different content."""


class TenantMismatch(EventStoreError):
    """An event for another tenant was offered to this tenant's store."""


@dataclass(frozen=True)
class StoredEvent:
    global_seq: int
    stream_version: int
    envelope: Envelope


@dataclass(frozen=True)
class AppendResult:
    appended: int
    skipped_duplicates: int
    last_global_seq: int | None


class EventStore(ABC):
    """No update or delete — by design."""

    @abstractmethod
    def append(self, events: Sequence[Envelope], expected_version: int | None = None) -> AppendResult:
        """Append atomically.

        ``expected_version`` (all events must then share one stream) is the
        stream's current version as last read by the caller; 0 = stream must
        be new. Re-appending an identical event_id is a no-op.
        """

    @abstractmethod
    def read_stream(self, tenant_id: str, stream_id: str) -> list[StoredEvent]: ...

    @abstractmethod
    def read_all(self, tenant_id: str, since: int | None = None) -> Iterable[StoredEvent]:
        """All events with global_seq > ``since`` in append order."""

    @abstractmethod
    def stream_version(self, tenant_id: str, stream_id: str) -> int: ...
