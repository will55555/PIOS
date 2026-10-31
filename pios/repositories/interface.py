"""The one persistence contract (ADR-012). Business logic depends on this, never on a database driver."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from pios.events import Envelope


@dataclass(frozen=True)
class StoredEvent:
    position: int
    event: Envelope


class Repository(ABC):
    """Append-only events plus projector positions, scoped per tenant. No update or delete, by design.

    Reads must pass every event through the upcaster chain before returning it (ADR-013).
    """

    @abstractmethod
    async def save_event(self, event: Envelope) -> int:
        """Append and return its position. A repeated idempotency_key is a no-op returning the first position."""

    @abstractmethod
    async def get_events_by_aggregate(self, tenant_id: str, aggregate_id: str) -> list[StoredEvent]: ...

    @abstractmethod
    async def get_events_after(self, tenant_id: str, position: int, limit: int = 100) -> list[StoredEvent]: ...

    @abstractmethod
    async def get_latest_position(self, tenant_id: str) -> int: ...

    @abstractmethod
    async def get_projector_position(self, tenant_id: str, projector: str) -> int: ...

    @abstractmethod
    async def set_projector_position(self, tenant_id: str, projector: str, position: int) -> None: ...
