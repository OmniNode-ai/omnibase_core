# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""LocalRuntimeBusAdapter typed result-transport tests (OMN-17859).

Barrier-2 RED->GREEN for the RuntimeLocal path: a def-B handler that returns a
``Sequence[BaseModel]`` (fan-out) or a single ``BaseModel`` whose topic varies by
class must publish to the contract-declared topic(s) via ``published_events`` —
NOT collapse to a single ``output_topic``. ``response`` preserves the returned
collection without publishing; only explicit ``event_fanout`` publishes N events.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.enum_result_transport import EnumResultTransport
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.dispatch.model_handler_output import ModelHandlerOutput
from omnibase_core.protocols.runtime.protocol_local_runtime_bus import (
    ProtocolLocalRuntimeBus,
)
from omnibase_core.protocols.runtime.protocol_local_runtime_callable_target import (
    ProtocolLocalRuntimeCallableTarget,
)
from omnibase_core.runtime.runtime_local_adapter import LocalRuntimeBusAdapter


class ModelInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0
    correlation_id: str = ""


class ModelAlpha(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


class ModelBeta(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


class ModelGamma(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: int = 0


# Canonical 5-segment ONEX topics (onex.{kind}.{producer}.{event-name}.v{n}) so
# the emit boundary can derive a non-null event_type (OMN-14743). A 4-segment
# topic yields no event_type and is fail-closed (see the dedicated event_type test).
_PUBLISHED = {"Alpha": "onex.evt.omni.alpha.v1", "Beta": "onex.evt.omni.beta.v1"}


class _FanoutHandler:
    """def-B fan-out: one input -> a two-element sequence of distinct classes."""

    def handle(self, request: ModelInput) -> tuple[ModelAlpha | ModelBeta, ...]:
        return (ModelAlpha(value=request.value), ModelBeta(value=request.value))


class _FanoutWithUnmappedHandler:
    """def-B fan-out containing a class absent from published_events."""

    def handle(self, request: ModelInput) -> tuple[ModelAlpha | ModelGamma, ...]:
        return (ModelAlpha(value=request.value), ModelGamma(value=request.value))


class _OpaqueFanoutHandler:
    """Returns a mixed batch that cannot be routed as typed events."""

    def handle(self, request: ModelInput) -> tuple[object, ...]:
        return (ModelAlpha(value=request.value), {"value": request.value})


class _SingleAlphaHandler:
    """def-B single-emit whose topic must come from published_events (Alpha)."""

    def handle(self, request: ModelInput) -> ModelAlpha:
        return ModelAlpha(value=request.value)


class _SingleUnmappedHandler:
    """def-B single-emit of a class ABSENT from published_events (fail-closed)."""

    def handle(self, request: ModelInput) -> ModelGamma:
        return ModelGamma(value=request.value)


class _ResponseListHandler:
    """Returns an ordered response collection, never a publish batch."""

    def handle(self, request: ModelInput) -> ModelHandlerOutput[list[ModelAlpha]]:
        return ModelHandlerOutput.for_compute(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="response-list",
            result=[
                ModelAlpha(value=request.value),
                ModelAlpha(value=request.value + 1),
            ],
        )


class _ResponseScalarHandler:
    def handle(self, request: ModelInput) -> ModelHandlerOutput[ModelAlpha]:
        return ModelHandlerOutput.for_compute(
            input_envelope_id=uuid4(),
            correlation_id=uuid4(),
            handler_id="response-scalar",
            result=ModelAlpha(value=request.value),
        )


class _RawResponseScalarHandler:
    def handle(self, request: ModelInput) -> ModelAlpha:
        return ModelAlpha(value=request.value)


class _RawResponseListHandler:
    def handle(self, request: ModelInput) -> list[ModelAlpha]:
        return [ModelAlpha(value=request.value), ModelAlpha(value=request.value + 1)]


class _LyingUnmappedFanoutHandler:
    """Declares valid ownership but returns a later unmapped element at runtime."""

    def handle(self, request: ModelInput) -> tuple[ModelAlpha, ...]:
        return (ModelAlpha(value=request.value), ModelGamma(value=request.value))  # type: ignore[return-value]


class _FakeBus:
    """Records ``publish`` calls; the adapter needs only ``publish`` here."""

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


def _msg(value: int) -> _FakeMsg:
    return _FakeMsg(json.dumps({"value": value, "correlation_id": "cid-1"}).encode())


def _adapter(
    handler: object,
    bus: _FakeBus,
    *,
    result_transport: EnumResultTransport,
    published_events: dict[str, str] | None,
    output_topic: str | None = "onex.evt.fallback.v1",
    on_error: Callable[[], None] | None = None,
    on_result: Callable[[object], None] | None = None,
) -> LocalRuntimeBusAdapter:
    return LocalRuntimeBusAdapter(
        handler=cast(ProtocolLocalRuntimeCallableTarget, handler),
        handler_name="test-handler",
        input_model_cls=ModelInput,
        output_topic=output_topic,
        bus=cast(ProtocolLocalRuntimeBus, bus),
        on_error=on_error,
        on_result=on_result,
        published_events=published_events,
        result_transport=result_transport,
    )


@pytest.mark.asyncio
async def test_explicit_event_fanout_publishes_two_topics_in_order() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _FanoutHandler(),
        bus,
        result_transport=EnumResultTransport.EVENT_FANOUT,
        published_events=_PUBLISHED,
    )
    await adapter.on_message(_msg(7))

    assert [topic for topic, _ in bus.published] == [
        "onex.evt.omni.alpha.v1",
        "onex.evt.omni.beta.v1",
    ]
    # OMN-14743: each emit is a ModelEventEnvelope carrying the topic-derived
    # event_type; the concrete model is the envelope payload, in return order.
    alpha = json.loads(bus.published[0][1])
    beta = json.loads(bus.published[1][1])
    assert alpha["payload"] == {"value": 7}
    assert alpha["event_type"] == "omni.alpha"
    assert beta["payload"] == {"value": 7}
    assert beta["event_type"] == "omni.beta"


@pytest.mark.asyncio
async def test_response_list_preserves_order_and_publishes_nothing() -> None:
    bus = _FakeBus()
    results: list[object] = []
    adapter = _adapter(
        _ResponseListHandler(),
        bus,
        result_transport=EnumResultTransport.RESPONSE,
        published_events=_PUBLISHED,
        on_result=results.append,
    )
    await adapter.on_message(_msg(7))

    assert results == [[ModelAlpha(value=7), ModelAlpha(value=8)]]
    assert bus.published == []


@pytest.mark.asyncio
async def test_response_scalar_exposes_result_not_output_wrapper() -> None:
    bus = _FakeBus()
    results: list[object] = []
    adapter = _adapter(
        _ResponseScalarHandler(),
        bus,
        result_transport=EnumResultTransport.RESPONSE,
        published_events=None,
        on_result=results.append,
    )

    await adapter.on_message(_msg(7))

    assert results == [ModelAlpha(value=7)]
    assert bus.published == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "expected"),
    [
        (_RawResponseScalarHandler(), ModelAlpha(value=7)),
        (
            _RawResponseListHandler(),
            [ModelAlpha(value=7), ModelAlpha(value=8)],
        ),
    ],
)
async def test_raw_response_preserves_scalar_or_ordered_list(
    handler: object, expected: object
) -> None:
    bus = _FakeBus()
    results: list[object] = []
    adapter = _adapter(
        handler,
        bus,
        result_transport=EnumResultTransport.RESPONSE,
        published_events=None,
        on_result=results.append,
    )

    await adapter.on_message(_msg(7))

    assert results == [expected]
    assert bus.published == []


def test_response_without_sink_fails_at_adapter_registration() -> None:
    with pytest.raises(ModelOnexError, match="on_result response sink"):
        _adapter(
            _ResponseScalarHandler(),
            _FakeBus(),
            result_transport=EnumResultTransport.RESPONSE,
            published_events=None,
        )


@pytest.mark.asyncio
async def test_explicit_event_fanout_single_emit_routes_via_published_events() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _SingleAlphaHandler(),
        bus,
        result_transport=EnumResultTransport.EVENT_FANOUT,
        published_events=_PUBLISHED,
    )
    await adapter.on_message(_msg(3))
    # Topic comes from the model's class, NOT the single output_topic.
    assert [topic for topic, _ in bus.published] == ["onex.evt.omni.alpha.v1"]


@pytest.mark.asyncio
async def test_explicit_event_fanout_without_mapping_fails_closed() -> None:
    bus = _FakeBus()
    with pytest.raises(ModelOnexError, match="not owned by contract"):
        _adapter(
            _SingleAlphaHandler(),
            bus,
            result_transport=EnumResultTransport.EVENT_FANOUT,
            published_events=None,
        )
    assert bus.published == []


@pytest.mark.asyncio
async def test_single_emit_unmapped_class_fails_closed() -> None:
    bus = _FakeBus()
    with pytest.raises(ModelOnexError, match="not owned by contract"):
        _adapter(
            _SingleUnmappedHandler(),
            bus,
            result_transport=EnumResultTransport.EVENT_FANOUT,
            published_events=_PUBLISHED,
        )
    assert bus.published == []


@pytest.mark.asyncio
async def test_fanout_batch_unmapped_class_fails_closed() -> None:
    bus = _FakeBus()
    with pytest.raises(ModelOnexError, match="not owned by contract"):
        _adapter(
            _FanoutWithUnmappedHandler(),
            bus,
            result_transport=EnumResultTransport.EVENT_FANOUT,
            published_events=_PUBLISHED,
        )
    assert bus.published == []


@pytest.mark.asyncio
async def test_fanout_opaque_batch_fails_before_any_send() -> None:
    """A mixed batch is rejected as a whole, never partially cross-published."""
    bus = _FakeBus()
    with pytest.raises(ModelOnexError, match="opaque or mixed"):
        _adapter(
            _OpaqueFanoutHandler(),
            bus,
            result_transport=EnumResultTransport.EVENT_FANOUT,
            published_events=_PUBLISHED,
        )
    assert bus.published == []


@pytest.mark.asyncio
async def test_lying_fanout_batch_is_fully_resolved_before_any_send() -> None:
    bus = _FakeBus()
    errors: list[bool] = []
    adapter = _adapter(
        _LyingUnmappedFanoutHandler(),
        bus,
        result_transport=EnumResultTransport.EVENT_FANOUT,
        published_events=_PUBLISHED,
        on_error=lambda: errors.append(True),
    )

    await adapter.on_message(_msg(1))

    assert bus.published == []
    assert errors == [True]
