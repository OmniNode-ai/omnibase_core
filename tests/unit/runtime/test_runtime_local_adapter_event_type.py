# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""RuntimeLocal fan-out emit stamps event_type on the envelope (OMN-14743).

The delegation stall: the RuntimeLocal fan-out publish path emitted the routing
intent as a RAW payload with NO envelope and NO ``event_type``, while the Kafka
applier stamped a topic-derived ``event_type``. The routing reducer's Kafka
consumer type-scopes its dispatcher on the ``event_type`` alias
(``omnibase-infra.delegation-routing-request``); an envelope whose ``event_type``
is null falls back to the payload class name (``ModelRoutingIntent``), matches NO
registered dispatcher, and is dropped — ``routing-decision.v1`` is never
published and the workflow stalls at ``RECEIVED``.

These tests pin the fix at the emit boundary: a fan-out emit MUST publish a
``ModelEventEnvelope`` carrying the exact topic-derived ``event_type`` the 07-11/13
working intents had, and a topic that yields no derivable ``event_type`` MUST
fail closed (raise) rather than emit a silently-dropped envelope.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    ModelDelegationRequest,
)
from omnibase_core.models.delegation.wire.model_orchestrator_intents import (
    ModelRoutingIntent,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter

# The exact live topic + the event_type the working 07-11/13 intents carried.
_ROUTING_REQUEST_TOPIC = "onex.cmd.omnibase-infra.delegation-routing-request.v1"
_EXPECTED_EVENT_TYPE = "omnibase-infra.delegation-routing-request"
# A non-canonical (4-segment) topic yields no derivable event_type -> fail-closed.
_NON_ONEX_TOPIC = "onex.evt.routingintent.v1"

_PUBLISHED_ROUTING = {"RoutingIntent": _ROUTING_REQUEST_TOPIC}
_PUBLISHED_NON_ONEX = {"RoutingIntent": _NON_ONEX_TOPIC}


def _delegation_request(correlation_id: str) -> ModelDelegationRequest:
    return ModelDelegationRequest(
        prompt="Write tests",
        task_type="test",
        correlation_id=UUID(correlation_id),
        emitted_at=datetime.now(UTC),
    )


class _RoutingIntentFanoutHandler:
    """def-B fan-out: returns a one-element sequence of ModelRoutingIntent."""

    def __init__(self, correlation_id: str) -> None:
        self._correlation_id = correlation_id

    def handle(self, request: object) -> tuple[ModelRoutingIntent, ...]:
        _ = request
        return (ModelRoutingIntent(payload=_delegation_request(self._correlation_id)),)


class _CapturingRoutingHandler:
    """Consume-side handler whose input model is ModelRoutingIntent (type-scoped)."""

    def __init__(self) -> None:
        self.received: list[object] = []

    def handle(self, intent: ModelRoutingIntent) -> None:
        self.received.append(intent)


class _FakeBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []

    async def start(self) -> None:  # pragma: no cover - unused
        return None

    async def close(self) -> None:  # pragma: no cover - unused
        return None

    async def publish(self, topic: str, key: object, value: bytes) -> object:
        self.published.append((topic, value))
        return None

    async def subscribe(
        self, topic: str, *, on_message: object, group_id: str
    ) -> object:  # pragma: no cover - unused
        return None


class _FakeMsg:
    def __init__(self, value: bytes) -> None:
        self.value = value


def _adapter(
    handler: object,
    bus: _FakeBus,
    *,
    published_events: dict[str, str],
    input_model_cls: type | None,
    on_error: Callable[[], None] | None = None,
) -> LocalRuntimeBusAdapter:
    return LocalRuntimeBusAdapter(
        handler=cast(ProtocolLocalRuntimeCallableTarget, handler),
        handler_name="test-routing-handler",
        input_model_cls=input_model_cls,  # type: ignore[arg-type]
        output_topic="onex.evt.fallback.v1",
        bus=cast(ProtocolLocalRuntimeBus, bus),
        on_error=on_error,
        published_events=published_events,
        multi_event_seam_enabled=True,
    )


def _input_msg(correlation_id: str) -> _FakeMsg:
    return _FakeMsg(json.dumps({"correlation_id": correlation_id}).encode())


@pytest.mark.asyncio
async def test_fanout_emit_stamps_topic_derived_event_type() -> None:
    """The gating fix: the emitted routing-intent envelope carries the event_type
    alias the reducer's type-scoped dispatcher matches — not a null value.

    RED before the fix: ``_publish_fanout`` published ``payload.model_dump_json()``
    (a raw ModelRoutingIntent, no ``event_type`` key), so this event_type
    assertion had no field to read and the reducer dispatcher dropped the message.
    """
    cid = str(uuid4())
    bus = _FakeBus()
    adapter = _adapter(
        _RoutingIntentFanoutHandler(cid),
        bus,
        published_events=_PUBLISHED_ROUTING,
        input_model_cls=None,  # operation_match entry: raw dict forwarded
    )

    await adapter.on_message(_input_msg(cid))

    assert [topic for topic, _ in bus.published] == [_ROUTING_REQUEST_TOPIC]
    wire = json.loads(bus.published[0][1])
    # The wire message is a ModelEventEnvelope, not a raw payload.
    assert wire["event_type"] == _EXPECTED_EVENT_TYPE
    assert wire["correlation_id"] == cid
    # The domain payload validates back into ModelRoutingIntent.
    intent = ModelRoutingIntent.model_validate(wire["payload"])
    assert intent.intent == "routing_reducer"
    assert str(intent.payload.correlation_id) == cid


@pytest.mark.asyncio
async def test_fanout_emit_fails_closed_on_non_derivable_event_type() -> None:
    """Fail-closed: a topic that yields no event_type must raise, not emit a
    null-event_type envelope the consuming dispatcher would silently drop.

    RED before the fix: the raw-payload emit published happily to any topic with
    no event_type at all — the exact silent-drop condition. Now the emit boundary
    converts it into a loud failure (on_error, nothing published).
    """
    cid = str(uuid4())
    bus = _FakeBus()
    errors: list[bool] = []
    adapter = _adapter(
        _RoutingIntentFanoutHandler(cid),
        bus,
        published_events=_PUBLISHED_NON_ONEX,
        input_model_cls=None,
        on_error=lambda: errors.append(True),
    )

    await adapter.on_message(_input_msg(cid))

    assert bus.published == []
    assert errors == [True]


@pytest.mark.asyncio
async def test_enveloped_message_round_trips_through_consume() -> None:
    """A subscribed adapter unwraps the fan-out envelope to the inner domain model.

    Proves the RuntimeLocal round-trip stays consistent: the emit publishes a
    ModelEventEnvelope; a consuming adapter whose input model is ModelRoutingIntent
    receives the inner ModelRoutingIntent (not the envelope), so the local
    delivery path agrees with the Kafka wire shape.
    """
    cid = str(uuid4())
    emit_bus = _FakeBus()
    emit_adapter = _adapter(
        _RoutingIntentFanoutHandler(cid),
        emit_bus,
        published_events=_PUBLISHED_ROUTING,
        input_model_cls=None,
    )
    await emit_adapter.on_message(_input_msg(cid))
    enveloped_bytes = emit_bus.published[0][1]

    capture = _CapturingRoutingHandler()
    consume_bus = _FakeBus()
    consume_adapter = _adapter(
        capture,
        consume_bus,
        published_events={},
        input_model_cls=ModelRoutingIntent,
    )

    await consume_adapter.on_message(_FakeMsg(enveloped_bytes))

    assert len(capture.received) == 1
    received = capture.received[0]
    assert isinstance(received, ModelRoutingIntent)
    assert str(received.payload.correlation_id) == cid
