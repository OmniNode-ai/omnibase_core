# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests for :func:`build_delivery_context` (OMN-15665).

The adapter surface that populates the canonical immutable delivery context AT
THE RECEIPT BOUNDARY: ``envelope_id`` comes from the consumer record's own wire
bytes (never re-derived from the pydantic-validated envelope, whose
``envelope_id`` field carries a ``default_factory=uuid4`` — that default would
silently fabricate an identity for a record that never truthfully carried one).
``topic`` / ``partition`` / ``offset`` are the broker coordinates, copied verbatim
from the polled transport message.
"""

from __future__ import annotations

import json
import uuid

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.runtime.runtime_delivery_context import build_delivery_context


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int = 1


def _wire_bytes(**overrides: object) -> bytes:
    envelope = ModelEventEnvelope(payload=_Payload())
    raw = json.loads(envelope.model_dump_json())
    raw.update(overrides)
    return json.dumps(raw).encode("utf-8")


def test_happy_path_copies_envelope_id_and_broker_coordinates_verbatim() -> None:
    real_id = uuid.uuid4()
    value = _wire_bytes(envelope_id=str(real_id))

    ctx = build_delivery_context(
        topic="onex.cmd.omnitest.x.v1", partition=3, offset=42, raw_value=value
    )

    assert ctx.envelope_id == real_id
    assert ctx.topic == "onex.cmd.omnitest.x.v1"
    assert ctx.partition == 3
    assert ctx.offset == 42


def test_missing_envelope_id_key_fails_closed_never_fabricates() -> None:
    real_id = uuid.uuid4()
    value = _wire_bytes(envelope_id=str(real_id))
    raw = json.loads(value)
    del raw["envelope_id"]
    stripped = json.dumps(raw).encode("utf-8")

    with pytest.raises(ModelOnexError):
        build_delivery_context(
            topic="onex.cmd.omnitest.x.v1", partition=0, offset=0, raw_value=stripped
        )


def test_null_envelope_id_fails_closed() -> None:
    value = _wire_bytes(envelope_id=None)

    with pytest.raises(ModelOnexError):
        build_delivery_context(
            topic="onex.cmd.omnitest.x.v1", partition=0, offset=0, raw_value=value
        )


def test_malformed_envelope_id_fails_closed() -> None:
    value = _wire_bytes(envelope_id="not-a-uuid")

    with pytest.raises(ModelOnexError):
        build_delivery_context(
            topic="onex.cmd.omnitest.x.v1", partition=0, offset=0, raw_value=value
        )


def test_non_json_wire_bytes_fail_closed() -> None:
    with pytest.raises(ModelOnexError):
        build_delivery_context(
            topic="onex.cmd.omnitest.x.v1",
            partition=0,
            offset=0,
            raw_value=b"not json at all",
        )


def test_correlation_id_never_replaces_envelope_id() -> None:
    """A distinct ``correlation_id`` on the wire must not alias or overwrite the
    authoritative ``envelope_id`` — the exact alias/fabrication class this ticket
    exists to prevent."""
    real_id = uuid.uuid4()
    other_correlation = uuid.uuid4()
    assert real_id != other_correlation
    value = _wire_bytes(envelope_id=str(real_id), correlation_id=str(other_correlation))

    ctx = build_delivery_context(
        topic="onex.cmd.omnitest.x.v1", partition=0, offset=0, raw_value=value
    )

    assert ctx.envelope_id == real_id
    assert ctx.envelope_id != other_correlation


def test_negative_broker_coordinate_is_rejected_not_silently_accepted() -> None:
    value = _wire_bytes(envelope_id=str(uuid.uuid4()))
    with pytest.raises(ModelOnexError):
        build_delivery_context(
            topic="onex.cmd.omnitest.x.v1", partition=-1, offset=0, raw_value=value
        )
