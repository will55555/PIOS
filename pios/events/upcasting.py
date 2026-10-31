"""Sequential upcaster chain, run by repositories on read. Unknown versions fail loudly (ADR-013)."""

from __future__ import annotations

from collections.abc import Callable

from pios.events.envelope import Envelope

Upcaster = Callable[[Envelope], Envelope]


class UnknownEventVersion(Exception):
    """An event's type or version has no known path to the current schema."""


class UpcasterRegistry:
    """Holds each type's current version and its one-version hops. Starts empty: no event types exist yet."""

    def __init__(self) -> None:
        self._current: dict[str, int] = {}
        self._hops: dict[tuple[str, int], Upcaster] = {}

    def register_type(self, event_type: str, current_version: int) -> None:
        self._current[event_type] = current_version

    def register_hop(self, event_type: str, from_version: int, upcaster: Upcaster) -> None:
        self._hops[(event_type, from_version)] = upcaster

    def upcast(self, event: Envelope) -> Envelope:
        current = self._current.get(event.type)
        if current is None:
            raise UnknownEventVersion(f"unregistered event type {event.type!r}")
        if event.schema_version > current:
            raise UnknownEventVersion(f"{event.type} v{event.schema_version} is newer than current v{current}")
        while event.schema_version < current:
            hop = self._hops.get((event.type, event.schema_version))
            if hop is None:
                raise UnknownEventVersion(f"no upcaster for {event.type} v{event.schema_version}")
            event = hop(event)
        return event
