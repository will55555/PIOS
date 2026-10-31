from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from pios_algo.events import Envelope, EventType, Meta


def test_valid_event_roundtrips(make_event):
    e = make_event()
    assert Envelope.from_json(e.to_json()) == e
    assert e.version == 1


def test_chain_ids_default_to_none(make_event):
    e = make_event()
    assert e.correlation_id is None and e.causation_id is None


def test_chain_ids_roundtrip(make_event, risk_id):
    parent = make_event()
    e = make_event(correlation_id=risk_id, causation_id=parent.event_id)
    back = Envelope.from_json(e.to_json())
    assert back.correlation_id == risk_id
    assert back.causation_id == parent.event_id


def test_chain_ids_must_be_uuids(make_event):
    with pytest.raises(ValidationError):
        make_event(correlation_id="not-a-uuid")


@pytest.mark.parametrize("bad", ["", "Will", "will/../x", "-will", "a b", "w" * 65])
def test_tenant_id_must_be_slug(make_event, bad):
    with pytest.raises(ValidationError):
        make_event(tenant_id=bad)


def test_naive_ts_rejected(make_event):
    with pytest.raises(ValidationError):
        make_event(ts=datetime(2026, 11, 2, 10, 45))


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_payload_blocked(make_event, value):
    with pytest.raises(ValidationError, match="non-finite"):
        make_event(payload={"ind": {"atr": [1.0, value]}})


@pytest.mark.parametrize("mode", ["live", "paper"])
def test_order_placed_needs_risk_check(make_event, mode):
    with pytest.raises(ValidationError, match="risk_check_id"):
        make_event(type=EventType.OrderPlaced, meta=Meta(source="engine", mode=mode))


def test_order_placed_with_risk_check_ok(make_event, risk_id):
    e = make_event(type=EventType.OrderPlaced, meta=Meta(source="engine", mode="live", risk_check_id=risk_id))
    assert e.meta.risk_check_id == risk_id


def test_order_placed_shadow_needs_no_risk_check(make_event):
    make_event(type=EventType.OrderPlaced, meta=Meta(source="engine", mode="shadow"))


def test_legacy_import_flag_only_for_claude(make_event):
    make_event(type=EventType.OrderPlaced, payload={"imported": True}, meta=Meta(source="claude", mode="live"))
    with pytest.raises(ValidationError):
        make_event(type=EventType.OrderPlaced, payload={"imported": True}, meta=Meta(source="engine", mode="live"))


@pytest.mark.parametrize(
    "etype",
    [EventType.AutonomyLevelChanged, EventType.FreezeSet, EventType.FreezeLifted, EventType.KillSwitchReset],
)
def test_tenant_only_types(make_event, etype):
    with pytest.raises(ValidationError, match="source='will'"):
        make_event(type=etype, stream="system", meta=Meta(source="claude"))
    make_event(type=etype, stream="system", meta=Meta(source="will"))


def test_envelope_is_frozen(make_event):
    e = make_event()
    with pytest.raises(ValidationError):
        e.stream_id = "x"  # type: ignore[misc]


def test_unknown_fields_rejected(make_event):
    raw = make_event().model_dump(mode="json")
    raw["surprise"] = 1
    with pytest.raises(ValidationError):
        Envelope.model_validate(raw)
