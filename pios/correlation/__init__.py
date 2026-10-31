"""Layer 5, correlation and causation: every event belongs to a traceable decision chain (ADR-011)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chain:
    """IDs for the next event in a chain. A root event has no cause."""

    correlation_id: uuid.UUID = field(default_factory=uuid.uuid4)
    causation_id: uuid.UUID | None = None

    def caused_by(self, event_id: uuid.UUID) -> Chain:
        return Chain(self.correlation_id, event_id)


__all__ = ["Chain"]
