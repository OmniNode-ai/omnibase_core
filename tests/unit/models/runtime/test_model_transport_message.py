# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for ``ModelTransportMessage`` (OMN-14719, epic OMN-14717).

Net-new, currently unused foundation. These tests lock the plan section (c)
contract: ``partition`` / ``offset`` REQUIRED, frozen, ``extra="forbid"``, opaque
``ack_token`` round-trips by identity.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.models.runtime import ModelTransportMessage
from omnibase_core.models.runtime.model_transport_message import (
    ModelTransportMessage as ModelTransportMessageDirect,
)

pytestmark = pytest.mark.unit


def _message(**overrides: object) -> ModelTransportMessage:
    kwargs: dict[str, object] = {
        "topic": "onex.cmd.example.v1",
        "partition": 0,
        "offset": 0,
        "key": None,
        "value": b"payload",
        "headers": {},
        "ack_token": object(),
    }
    kwargs.update(overrides)
    return ModelTransportMessage(**kwargs)  # type: ignore[arg-type]  # NOTE(OMN-14719)


def test_reexport_is_same_class() -> None:
    assert ModelTransportMessage is ModelTransportMessageDirect


def test_construct_full_message_round_trips_fields() -> None:
    token = object()
    msg = ModelTransportMessage(
        topic="onex.cmd.example.v1",
        partition=3,
        offset=42,
        key=b"route-key",
        value=b"payload-bytes",
        headers={"content-type": b"application/json"},
        ack_token=token,
    )

    assert msg.topic == "onex.cmd.example.v1"
    assert msg.partition == 3
    assert msg.offset == 42
    assert msg.key == b"route-key"
    assert msg.value == b"payload-bytes"
    assert msg.headers == {"content-type": b"application/json"}
    # ack_token is opaque and preserved by identity — the runtime hands it back as-is.
    assert msg.ack_token is token


def test_partition_is_required() -> None:
    with pytest.raises(ValidationError, match="partition"):
        ModelTransportMessage(
            topic="t",
            offset=0,
            key=None,
            value=b"",
            headers={},
            ack_token=object(),
        )  # type: ignore[call-arg]  # NOTE(OMN-14719)


def test_offset_is_required() -> None:
    with pytest.raises(ValidationError, match="offset"):
        ModelTransportMessage(
            topic="t",
            partition=0,
            key=None,
            value=b"",
            headers={},
            ack_token=object(),
        )  # type: ignore[call-arg]  # NOTE(OMN-14719)


def test_key_none_is_accepted() -> None:
    assert _message(key=None).key is None


def test_key_bytes_is_accepted() -> None:
    assert _message(key=b"k").key == b"k"


def test_model_is_frozen() -> None:
    msg = _message()
    with pytest.raises(ValidationError):
        msg.offset = 99  # type: ignore[misc]  # NOTE(OMN-14719)


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        _message(unexpected="nope")


def test_extra_forbid_is_configured() -> None:
    assert ModelTransportMessage.model_config.get("extra") == "forbid"
    assert ModelTransportMessage.model_config.get("frozen") is True
