"""Layer 2, projections: derived read models with per-projector position tracking. Rebuilds are manual (ADR-014)."""

from __future__ import annotations

from typing import Protocol

from pios.events import Envelope


class Projector(Protocol):
    """Consumes events in order. Its position lives in the repository, isolated from every other projector."""

    @property
    def name(self) -> str: ...

    async def handle(self, event: Envelope) -> None: ...


__all__ = ["Projector"]
