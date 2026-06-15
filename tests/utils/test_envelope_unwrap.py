# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tests for the single transport-envelope unwrap predicate (OMN-12960).

These are the consolidated coverage for the predicate that previously lived as
two hand-synced copies in omnibase_infra and omnimarket. The materialized-shape
cases are the regression guard for the OMN-12946 / OMN-12960 drift: the marker
set MUST recognise the dispatch-engine materialized outer keys
(``{"payload", "__bindings", "__debug_trace"}``).
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.utils.util_envelope_unwrap import (
    ENVELOPE_MARKER_KEYS,
    is_transport_envelope,
    unwrap_transport_envelope,
)


class _Domain(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: str
    value: int


class _EnvelopeLike:
    """Object exposing a ``.payload`` attribute, like ``ModelEventEnvelope``."""

    def __init__(self, payload: object) -> None:
        self.payload = payload


def _domain_dict() -> dict[str, object]:
    return {"correlation_id": "cid-1", "value": 7}


def test_marker_set_covers_materialized_dispatch_keys() -> None:
    """The marker set must intersect the dispatch-engine materialized shape.

    ``unwrap_transport_envelope`` only unwraps when ``ENVELOPE_MARKER_KEYS``
    intersects the outer mapping's keys. The dispatch engine's materialized
    outer keys are ``{"payload", "__bindings", "__debug_trace"}`` — if neither
    ``__bindings`` nor ``__debug_trace`` is in the marker set the live unwrap
    silently no-ops. This is the regression that OMN-12960 makes structurally
    impossible by collapsing the two hand-synced sets into this one source.
    """
    materialized_outer_keys = {"payload", "__bindings", "__debug_trace"}
    assert ENVELOPE_MARKER_KEYS & materialized_outer_keys
    assert "__bindings" in ENVELOPE_MARKER_KEYS
    assert "__debug_trace" in ENVELOPE_MARKER_KEYS


def test_unwraps_bare_marker_envelope() -> None:
    env = {"payload": _domain_dict(), "partition_key": None}
    assert unwrap_transport_envelope(env) == _domain_dict()


def test_unwraps_materialized_dispatch_envelope() -> None:
    env = {
        "payload": _domain_dict(),
        "__bindings": {"k": "v"},
        "__debug_trace": {"topic": "t"},
    }
    assert unwrap_transport_envelope(env) == _domain_dict()


def test_unwraps_materialized_envelope_with_only_bindings_marker() -> None:
    """The exact OMN-12960 drift case: only ``__bindings`` present.

    The pre-OMN-12960 infra marker set lacked ``__bindings``; a materialized
    envelope whose only top-level marker was ``__bindings`` failed to unwrap on
    the infra side while unwrapping on the omnimarket side. The single source
    handles it unconditionally.
    """
    env = {"payload": _domain_dict(), "__bindings": {"k": "v"}}
    assert unwrap_transport_envelope(env) == _domain_dict()


def test_unwraps_double_wrapped_envelope() -> None:
    inner = {"payload": _domain_dict(), "partition_key": None}
    outer = {"payload": inner, "__debug_trace": {"topic": "t"}}
    assert unwrap_transport_envelope(outer) == _domain_dict()


def test_unwraps_object_with_payload_attribute() -> None:
    env = _EnvelopeLike(_domain_dict())
    assert unwrap_transport_envelope(env) == _domain_dict()


def test_unwraps_nested_object_then_mapping() -> None:
    env = _EnvelopeLike({"payload": _domain_dict(), "event_type": "x"})
    assert unwrap_transport_envelope(env) == _domain_dict()


def test_bare_domain_dict_passthrough() -> None:
    """A domain dict with no ``payload`` field is returned unchanged."""
    assert unwrap_transport_envelope(_domain_dict()) == _domain_dict()


def test_domain_model_with_payload_field_not_unwrapped() -> None:
    """A mapping with a ``payload`` field but no marker is NOT an envelope."""
    legit = {"payload": {"some": "domain-data"}}
    assert unwrap_transport_envelope(legit) == legit


def test_domain_model_instance_passthrough() -> None:
    """A model instance with no ``.payload`` attribute is returned unchanged."""
    model = _Domain(correlation_id="cid-1", value=7)
    assert unwrap_transport_envelope(model) is model


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ({"payload": {"a": 1}, "partition_key": None}, True),
        ({"payload": {"a": 1}, "__bindings": {}}, True),
        ({"payload": {"a": 1}, "__debug_trace": {}}, True),
        ({"payload": {"a": 1}}, False),  # no marker
        ({"partition_key": None}, False),  # no payload mapping
        ({"payload": "not-a-mapping", "partition_key": None}, False),
        ("not-a-mapping", False),
    ],
)
def test_is_transport_envelope(value: object, expected: bool) -> None:
    assert is_transport_envelope(value) is expected
