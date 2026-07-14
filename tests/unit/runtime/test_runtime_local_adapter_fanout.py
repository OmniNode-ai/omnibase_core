# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""LocalRuntimeBusAdapter def-B multi-event (fan-out) publish tests (OMN-14403 §6ii).

Barrier-2 RED->GREEN for the RuntimeLocal path: a def-B handler that returns a
``Sequence[BaseModel]`` (fan-out) or a single ``BaseModel`` whose topic varies by
class must publish to the contract-declared topic(s) via ``published_events`` —
NOT collapse to a single ``output_topic``. The seam is default-OFF; these tests
assert both the OFF (unchanged / warn-drop) and ON (publish N) behavior.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import cast

import pytest
from pydantic import BaseModel, ConfigDict

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


_PUBLISHED = {"Alpha": "onex.evt.alpha.v1", "Beta": "onex.evt.beta.v1"}


class _FanoutHandler:
    """def-B fan-out: one input -> a two-element sequence of distinct classes."""

    def handle(self, request: ModelInput) -> tuple[BaseModel, ...]:
        return (ModelAlpha(value=request.value), ModelBeta(value=request.value))


class _SingleAlphaHandler:
    """def-B single-emit whose topic must come from published_events (Alpha)."""

    def handle(self, request: ModelInput) -> BaseModel:
        return ModelAlpha(value=request.value)


class _SingleUnmappedHandler:
    """def-B single-emit of a class ABSENT from published_events (fail-closed)."""

    def handle(self, request: ModelInput) -> BaseModel:
        return ModelGamma(value=request.value)


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
    seam_enabled: bool,
    published_events: dict[str, str] | None,
    output_topic: str | None = "onex.evt.fallback.v1",
    on_error: Callable[[], None] | None = None,
) -> LocalRuntimeBusAdapter:
    return LocalRuntimeBusAdapter(
        handler=cast("ProtocolLocalRuntimeCallableTarget", handler),
        handler_name="test-handler",
        input_model_cls=ModelInput,
        output_topic=output_topic,
        bus=cast("ProtocolLocalRuntimeBus", bus),
        on_error=on_error,
        published_events=published_events,
        multi_event_seam_enabled=seam_enabled,
    )


@pytest.mark.asyncio
async def test_fanout_seam_on_publishes_two_topics_in_order() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _FanoutHandler(), bus, seam_enabled=True, published_events=_PUBLISHED
    )
    await adapter.on_message(_msg(7))

    assert [topic for topic, _ in bus.published] == [
        "onex.evt.alpha.v1",
        "onex.evt.beta.v1",
    ]
    # Payloads are the concrete models, in return order.
    alpha = json.loads(bus.published[0][1])
    beta = json.loads(bus.published[1][1])
    assert alpha == {"value": 7}
    assert beta == {"value": 7}


@pytest.mark.asyncio
async def test_fanout_seam_off_drops_and_publishes_nothing() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _FanoutHandler(), bus, seam_enabled=False, published_events=_PUBLISHED
    )
    await adapter.on_message(_msg(7))
    # Seam OFF: warn-drop the sequence, publish nothing (the census channel).
    assert bus.published == []


@pytest.mark.asyncio
async def test_single_emit_seam_on_routes_via_published_events() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _SingleAlphaHandler(), bus, seam_enabled=True, published_events=_PUBLISHED
    )
    await adapter.on_message(_msg(3))
    # Topic comes from the model's class, NOT the single output_topic.
    assert [topic for topic, _ in bus.published] == ["onex.evt.alpha.v1"]


@pytest.mark.asyncio
async def test_single_emit_seam_off_uses_output_topic() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _SingleAlphaHandler(), bus, seam_enabled=False, published_events=_PUBLISHED
    )
    await adapter.on_message(_msg(3))
    # Seam OFF: unchanged — single output_topic path.
    assert [topic for topic, _ in bus.published] == ["onex.evt.fallback.v1"]


@pytest.mark.asyncio
async def test_single_emit_seam_on_no_published_events_uses_output_topic() -> None:
    bus = _FakeBus()
    adapter = _adapter(
        _SingleAlphaHandler(), bus, seam_enabled=True, published_events=None
    )
    await adapter.on_message(_msg(3))
    # No published_events declared -> unchanged single output_topic path.
    assert [topic for topic, _ in bus.published] == ["onex.evt.fallback.v1"]


@pytest.mark.asyncio
async def test_fanout_unmapped_class_fails_closed() -> None:
    bus = _FakeBus()
    errors: list[bool] = []

    def _on_error() -> None:
        errors.append(True)

    adapter = _adapter(
        _SingleUnmappedHandler(),
        bus,
        seam_enabled=True,
        published_events=_PUBLISHED,
        on_error=_on_error,
    )
    await adapter.on_message(_msg(1))
    # Fail-closed: unmapped class raises inside publish -> on_error, nothing sent.
    assert bus.published == []
    assert errors == [True]
