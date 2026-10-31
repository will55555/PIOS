"""ADR-013: known versions upcast one hop at a time, anything unknown fails loudly."""

from __future__ import annotations

import pytest

from pios.events import Envelope, UnknownEventVersion, UpcasterRegistry


def _bump(event: Envelope) -> Envelope:
    return event.model_copy(update={"schema_version": event.schema_version + 1})


def test_current_version_passes_through(make_event):
    registry = UpcasterRegistry()
    registry.register_type("TestEvent", 1)
    event = make_event()
    assert registry.upcast(event) == event


def test_old_version_walks_the_chain(make_event):
    registry = UpcasterRegistry()
    registry.register_type("TestEvent", 3)
    registry.register_hop("TestEvent", 1, _bump)
    registry.register_hop("TestEvent", 2, _bump)
    assert registry.upcast(make_event()).schema_version == 3


def test_unregistered_type_fails(make_event):
    with pytest.raises(UnknownEventVersion):
        UpcasterRegistry().upcast(make_event())


def test_future_version_fails(make_event):
    registry = UpcasterRegistry()
    registry.register_type("TestEvent", 1)
    with pytest.raises(UnknownEventVersion):
        registry.upcast(make_event(schema_version=2))


def test_gap_in_the_chain_fails(make_event):
    registry = UpcasterRegistry()
    registry.register_type("TestEvent", 2)
    with pytest.raises(UnknownEventVersion):
        registry.upcast(make_event())
