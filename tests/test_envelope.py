from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from pios.correlation import Chain
from pios.tenancy import schema_name, validate_tenant_id


def test_valid_event_is_frozen(make_event):
    event = make_event()
    with pytest.raises(ValidationError):
        event.type = "Other"


def test_correlation_id_is_required(make_event):
    with pytest.raises(ValidationError):
        make_event(correlation_id=None)


def test_naive_timestamp_is_rejected(make_event):
    with pytest.raises(ValidationError):
        make_event(occurred_at=datetime(2026, 10, 31, 12, 0))


def test_float_in_payload_is_rejected(make_event):
    with pytest.raises(ValidationError, match="payload.fill.price"):
        make_event(payload={"fill": {"price": 348.94}})


def test_minor_units_and_decimal_strings_are_allowed(make_event):
    event = make_event(payload={"amount_cents": 34894, "price": "0.00071"})
    assert event.payload["price"] == "0.00071"


def test_unknown_field_is_rejected(make_event):
    with pytest.raises(ValidationError):
        make_event(extra_field=1)


def test_chain_keeps_correlation_and_links_cause():
    root = Chain()
    cause = uuid.uuid4()
    next_link = root.caused_by(cause)
    assert root.causation_id is None
    assert next_link.correlation_id == root.correlation_id
    assert next_link.causation_id == cause


def test_tenant_ids():
    assert schema_name("will") == "tenant_will"
    with pytest.raises(ValueError):
        validate_tenant_id("Will; DROP SCHEMA")
