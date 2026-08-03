# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests: RuntimeDispatch wires the delivery context at the receipt
boundary (OMN-15665).

Design constraints under test:

* The delivery context is RuntimeDispatch-context-resident, NEVER a def-B handler
  argument — ``handle(request) -> response`` stays exactly one parameter.
* ``delivery_receipt_adapter_factory`` is optional and keyword-only with a
  ``None`` default. THIS IS THE FIX for the 2026-08-02 CORE-PASS / CROSS-REPO-FAIL
  defect: a required keyword-only constructor argument broke every existing
  ``RuntimeDispatch(...)`` call site (``omnibase_infra`` composition, S6/S8
  integration tests) that does not know about delivery receipts. Existing
  composition roots that omit the factory must keep working unchanged and must
  report ``delivery_receipts_enabled is False`` — no durable-receipt claim there.
* When configured, the factory receives the SAME immutable
  ``ModelDeliveryContext`` built from the actual polled record (never fabricated)
  before the message becomes committable, and its zero-arg receipt-ack callable is
  awaited before COMMIT. A receipt-adapter failure redelivers the message (never
  silently commits past an unacknowledged receipt).
* A record whose wire bytes lack a truthful ``envelope_id`` is redelivered / DLQ'd
  — never silently committed with a fabricated identity — even with no receipt
  adapter configured at all (the context's fail-closed guarantee is unconditional).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext
from omnibase_core.runtime.runtime_dispatch import DispatchRoute, RuntimeDispatch
from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
from omnibase_core.runtime.transport.runtime_in_memory_transport import (
    InMemoryTransport,
)

pytestmark = pytest.mark.asyncio

IN_TOPIC = "onex.cmd.omnitest.receipt.v1"
OUT_TOPIC = "onex.evt.omnitest.receipt-echoed.v1"


class ModelEcho(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int


class ModelEchoed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int


class EchoHandler:
    """def-B handler; records exactly what it was invoked with (never a context)."""

    def __init__(self) -> None:
        self.received_types: list[type] = []

    async def handle(self, request: ModelEcho) -> ModelEchoed:
        self.received_types.append(type(request))
        return ModelEchoed(n=request.n)


@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


@pytest.fixture
def producer(broker: InMemoryBroker) -> InMemoryTransport:
    return InMemoryTransport(broker=broker, group="producer")


def _consumer(broker: InMemoryBroker, *, group: str) -> InMemoryTransport:
    return InMemoryTransport(broker=broker, group=group, topics=[IN_TOPIC])


async def _seed_raw(producer: InMemoryTransport, value: bytes) -> None:
    await producer.send(IN_TOPIC, key=None, value=value, headers={})


async def _seed(producer: InMemoryTransport, n: int = 1) -> ModelEventEnvelope[object]:
    envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
        payload=ModelEcho(n=n), correlation_id=uuid4()
    )
    await producer.send(
        IN_TOPIC, key=None, value=envelope.model_dump_json().encode("utf-8"), headers={}
    )
    return envelope


def _route(handler: EchoHandler) -> DispatchRoute:
    return DispatchRoute(
        name="echo",
        handler=handler,  # type: ignore[arg-type]
        published_events={"ModelEchoed": OUT_TOPIC},
        input_model_cls=ModelEcho,
    )


class TestBackwardCompatibility:
    """Existing composition roots that omit the factory keep working (the exact
    defect class the 2026-08-02 lane hit at omnibase_infra composition.py:430)."""

    async def test_constructor_does_not_require_the_factory(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        transport = _consumer(broker, group="g")
        handler = EchoHandler()
        # No delivery_receipt_adapter_factory kwarg at all — must not TypeError.
        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(handler)},
        )
        assert dispatch.delivery_receipts_enabled is False

        await _seed(producer)
        processed = await dispatch.drain()
        assert processed == 1
        assert handler.received_types == [ModelEcho]

    async def test_delivery_receipts_enabled_true_when_factory_injected(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        transport = _consumer(broker, group="g2")

        def _factory(
            context: ModelDeliveryContext,
        ) -> Callable[[], Awaitable[None]]:
            async def _ack() -> None:
                return None

            return _ack

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(EchoHandler())},
            delivery_receipt_adapter_factory=_factory,
        )
        assert dispatch.delivery_receipts_enabled is True


class TestReceiptBoundary:
    async def test_factory_receives_truthful_context_before_commit(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        transport = _consumer(broker, group="g3")
        seen_contexts: list[ModelDeliveryContext] = []

        def _factory(
            context: ModelDeliveryContext,
        ) -> Callable[[], Awaitable[None]]:
            seen_contexts.append(context)

            async def _ack() -> None:
                return None

            return _ack

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(EchoHandler())},
            delivery_receipt_adapter_factory=_factory,
        )
        envelope = await _seed(producer, n=9)
        processed = await dispatch.drain()

        assert processed == 1
        assert len(seen_contexts) == 1
        ctx = seen_contexts[0]
        assert ctx.envelope_id == envelope.envelope_id
        assert ctx.topic == IN_TOPIC
        assert ctx.partition == 0
        assert ctx.offset == 0
        assert broker.committed_offset(IN_TOPIC, "g3", 0) == 0

    async def test_correlation_id_never_aliases_envelope_id_at_the_boundary(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        transport = _consumer(broker, group="g4")
        seen_contexts: list[ModelDeliveryContext] = []

        def _factory(
            context: ModelDeliveryContext,
        ) -> Callable[[], Awaitable[None]]:
            seen_contexts.append(context)

            async def _ack() -> None:
                return None

            return _ack

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(EchoHandler())},
            delivery_receipt_adapter_factory=_factory,
        )
        distinct_correlation: UUID = UUID(int=123456789)
        envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
            payload=ModelEcho(n=1), correlation_id=distinct_correlation
        )
        await producer.send(
            IN_TOPIC,
            key=None,
            value=envelope.model_dump_json().encode("utf-8"),
            headers={},
        )
        await dispatch.drain()

        assert len(seen_contexts) == 1
        assert seen_contexts[0].envelope_id == envelope.envelope_id
        assert seen_contexts[0].envelope_id != distinct_correlation

    async def test_receipt_adapter_failure_redelivers_not_commits(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        transport = _consumer(broker, group="g5")
        attempts = {"n": 0}

        def _factory(
            context: ModelDeliveryContext,
        ) -> Callable[[], Awaitable[None]]:
            async def _ack() -> None:
                attempts["n"] += 1
                if attempts["n"] == 1:
                    raise RuntimeError("durable receipt store unavailable")

            return _ack

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(EchoHandler())},
            delivery_receipt_adapter_factory=_factory,
        )
        await _seed(producer)
        processed = await dispatch.drain()

        # First attempt: receipt ack raises -> REDELIVER (no commit this round).
        # drain() keeps polling until empty, so the retry succeeds within the loop.
        assert processed >= 1
        assert attempts["n"] == 2
        assert broker.committed_offset(IN_TOPIC, "g5", 0) == 0

    async def test_handler_never_receives_the_delivery_context(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """def-B stays exactly one parameter — the context never pollutes it."""
        transport = _consumer(broker, group="g6")
        handler = EchoHandler()

        def _factory(
            context: ModelDeliveryContext,
        ) -> Callable[[], Awaitable[None]]:
            async def _ack() -> None:
                return None

            return _ack

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(handler)},
            delivery_receipt_adapter_factory=_factory,
        )
        await _seed(producer)
        await dispatch.drain()

        assert handler.received_types == [ModelEcho]


class TestFailClosedAbsenceUnconditional:
    """The context's fail-closed guarantee applies even with NO receipt adapter
    configured — it is never a fabricated identity, ever."""

    async def test_missing_envelope_id_on_wire_is_never_silently_committed(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        import json

        transport = _consumer(broker, group="g7")
        envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
            payload=ModelEcho(n=1)
        )
        raw = json.loads(envelope.model_dump_json())
        del raw["envelope_id"]
        stripped = json.dumps(raw).encode("utf-8")

        dispatch = RuntimeDispatch(
            consumer=transport,
            producer=producer,
            routing_map={IN_TOPIC: _route(EchoHandler())},
        )
        await _seed_raw(producer, stripped)
        await dispatch.drain()

        # Never committed with a fabricated envelope_id — it is redelivered until
        # retries exhaust, then dead-lettered (durable evidence), but the original
        # offset must not silently commit.
        assert len(broker.records(f"{IN_TOPIC}.dlq", 0)) == 1
        assert broker.committed_offset(IN_TOPIC, "g7", 0) == 0
