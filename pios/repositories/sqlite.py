"""SQLite repository for development and tests (ADR-012). Stub until the learning gate clears."""

from __future__ import annotations

from pathlib import Path

from pios.events import Envelope, UpcasterRegistry
from pios.repositories.interface import Repository, StoredEvent


class SqliteRepository(Repository):
    def __init__(self, root: Path | str, upcasters: UpcasterRegistry) -> None:
        self.root = Path(root)
        self.upcasters = upcasters

    async def save_event(self, event: Envelope) -> int:
        raise NotImplementedError

    async def get_events_by_aggregate(self, tenant_id: str, aggregate_id: str) -> list[StoredEvent]:
        raise NotImplementedError

    async def get_events_after(self, tenant_id: str, position: int, limit: int = 100) -> list[StoredEvent]:
        raise NotImplementedError

    async def get_latest_position(self, tenant_id: str) -> int:
        raise NotImplementedError

    async def get_projector_position(self, tenant_id: str, projector: str) -> int:
        raise NotImplementedError

    async def set_projector_position(self, tenant_id: str, projector: str, position: int) -> None:
        raise NotImplementedError
