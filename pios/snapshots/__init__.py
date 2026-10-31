"""Layer 3, snapshots: interface designed, deliberately not built until replay time is a real problem (ADR-014)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Snapshot:
    projector: str
    position: int
    state: dict[str, Any]


class SnapshotStore(Protocol):
    async def save_snapshot(self, tenant_id: str, snapshot: Snapshot) -> None: ...

    async def load_snapshot(self, tenant_id: str, projector: str) -> Snapshot | None: ...


__all__ = ["Snapshot", "SnapshotStore"]
