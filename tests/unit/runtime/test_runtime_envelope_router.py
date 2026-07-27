# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit tests for the runtime envelope boundary (OMN-14747, epic OMN-14717).

Covers the two load-bearing seams in isolation:

* :func:`derive_event_type_from_topic` — the ONEX topic -> ``event_type`` derivation.
* :func:`wrap_outbound_envelope` — the OUTBOUND envelope contract and, critically, the
  OMN-14743 fail-closed guarantee: it RAISES rather than emit a null-``event_type``
  event, and it bans the ``uuid4`` correlation fallback (deterministic ids).
* :func:`decode_inbound_envelope` — the INBOUND wire-bytes -> envelope boundary.
"""

from __future__ import annotations

from uuid import uuid4, uuid5

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.runtime.runtime_envelope_router import (
    CAUSATION_ID_TAG,
    decode_inbound_envelope,
    derive_event_type_from_topic,
    wrap_outbound_envelope,
)


class _Evt(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int


class TestDeriveEventTypeFromTopic:
    def test_valid_onex_topic_derives_producer_dot_event(self) -> None:
        assert (
            derive_event_type_from_topic("onex.evt.omnimarket.swarm-health-done.v1")
            == "omnimarket.swarm-health-done"
        )

    def test_command_topic_also_derives(self) -> None:
        assert (
            derive_event_type_from_topic("onex.cmd.omnitest.double.v1")
            == "omnitest.double"
        )

    @pytest.mark.parametrize(
        "topic",
        [
            "legacy_topic",
            "not.enough.parts",
            "kafka.evt.producer.event.v1",  # first segment is not 'onex'
            "",
        ],
    )
    def test_non_onex_or_malformed_topic_returns_none(self, topic: str) -> None:
        assert derive_event_type_from_topic(topic) is None


class TestWrapOutboundEnvelope:
    def test_stamps_event_type_correlation_causation_and_deterministic_id(self) -> None:
        corr = uuid4()
        inbound = ModelEventEnvelope(payload={"n": 1}, correlation_id=corr)
        topic = "onex.evt.omnitest.double-done.v1"

        out = wrap_outbound_envelope(
            _Evt(value=42), inbound_envelope=inbound, idx=0, topic=topic
        )

        assert out.event_type == "omnitest.double-done"
        assert out.correlation_id == corr
        assert out.metadata.tags[CAUSATION_ID_TAG] == str(inbound.envelope_id)
        assert out.envelope_id == uuid5(corr, "_Evt:0")
        assert out.payload_type == "_Evt"
        assert isinstance(out.payload, _Evt)

    def test_deterministic_id_is_reproducible_across_calls(self) -> None:
        corr = uuid4()
        inbound = ModelEventEnvelope(payload={}, correlation_id=corr)
        topic = "onex.evt.omnitest.double-done.v1"
        first = wrap_outbound_envelope(
            _Evt(value=1), inbound_envelope=inbound, idx=2, topic=topic
        )
        second = wrap_outbound_envelope(
            _Evt(value=1), inbound_envelope=inbound, idx=2, topic=topic
        )
        # Same correlation + type + idx => identical envelope_id (at-least-once dedupe).
        assert first.envelope_id == second.envelope_id

    def test_fail_closed_on_null_event_type_omn_14743(self) -> None:
        """RED-proof: a non-ONEX topic would derive a null event_type -> RAISE."""
        inbound = ModelEventEnvelope(payload={}, correlation_id=uuid4())
        with pytest.raises(ModelOnexError, match="event_type is null"):
            wrap_outbound_envelope(
                _Evt(value=1),
                inbound_envelope=inbound,
                idx=0,
                topic="legacy_non_onex_topic",
            )

    def test_fail_closed_on_missing_correlation_id_bans_uuid4(self) -> None:
        inbound = ModelEventEnvelope(payload={}, correlation_id=None)
        with pytest.raises(ModelOnexError, match=r"no.*correlation_id"):
            wrap_outbound_envelope(
                _Evt(value=1),
                inbound_envelope=inbound,
                idx=0,
                topic="onex.evt.omnitest.double-done.v1",
            )


class TestDecodeInboundEnvelope:
    def test_roundtrip_preserves_payload_and_correlation(self) -> None:
        corr = uuid4()
        inbound = ModelEventEnvelope(payload={"n": 7}, correlation_id=corr)
        decoded = decode_inbound_envelope(inbound.model_dump_json().encode("utf-8"))
        assert decoded.correlation_id == corr
        assert decoded.payload == {"n": 7}
        assert decoded.envelope_id == inbound.envelope_id

    def test_fail_closed_on_non_envelope_bytes(self) -> None:
        with pytest.raises(ModelOnexError, match="decode inbound"):
            decode_inbound_envelope(b"not-json-at-all")
