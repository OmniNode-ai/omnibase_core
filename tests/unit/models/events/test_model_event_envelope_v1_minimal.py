# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for EventEnvelopeV1Minimal (migrated from omnibase_compat OMN-12188)."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.models.events.model_event_envelope_v1_minimal import (
    EventEnvelopeV1Minimal,
)


@pytest.mark.unit
def test_event_envelope_roundtrip() -> None:
    eid = uuid4()
    envelope = EventEnvelopeV1Minimal(
        event_id=eid,
        event_type="node.executed.v1",
        payload={"result": "ok"},
    )
    serialized = envelope.model_dump_json()
    restored = EventEnvelopeV1Minimal.model_validate_json(serialized)
    assert restored.event_id == envelope.event_id
    assert restored.event_type == envelope.event_type
    assert restored.payload == envelope.payload


@pytest.mark.unit
def test_event_envelope_is_frozen() -> None:
    envelope = EventEnvelopeV1Minimal(
        event_id=uuid4(),
        event_type="node.executed.v1",
        payload={},
    )
    with pytest.raises((ValidationError, TypeError)):
        envelope.event_id = uuid4()  # type: ignore[misc]


@pytest.mark.unit
def test_event_envelope_schema_export() -> None:
    schema = EventEnvelopeV1Minimal.model_json_schema()
    assert set(schema["properties"].keys()) == {
        "event_id",
        "event_type",
        "payload",
        "schema_version",
        "data_provenance",
    }


@pytest.mark.unit
def test_event_envelope_defaults() -> None:
    envelope = EventEnvelopeV1Minimal(event_type="test.v1")
    assert envelope.schema_version == "1.0"
    assert envelope.data_provenance is None
    assert envelope.payload == {}
    assert isinstance(envelope.event_id, UUID)


@pytest.mark.unit
def test_event_envelope_data_provenance_values() -> None:
    for label in (
        "demo_seeded",
        "demo_projected_shortcut",
        "measured",
        "estimated",
        "unknown",
    ):
        envelope = EventEnvelopeV1Minimal(event_type="test.v1", data_provenance=label)
        assert envelope.data_provenance == label


@pytest.mark.unit
def test_event_envelope_exported_from_events_init() -> None:
    from omnibase_core.models.events import EventEnvelopeV1Minimal as Imported

    assert Imported is EventEnvelopeV1Minimal
