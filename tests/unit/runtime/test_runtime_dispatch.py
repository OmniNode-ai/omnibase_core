# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unit + in-memory golden-chain tests for RuntimeDispatch (OMN-14747, epic OMN-14717).

Drives the ONE runtime end-to-end over the in-memory transport (S2) — the substrate
whose Kafka-faithful semantics (proven by the S2 conformance suite) license
"in-memory golden chain => Kafka golden chain". Coverage:

* the ONE coercion — ``operation_match`` (annotation-driven) and ``payload_type_match``;
* fan-out — single-emit and ordered multi-event through the shared resolver;
* the in-memory golden chain — input command -> dispatch -> N emitted envelopes, each
  carrying a NON-NULL ``event_type`` + propagated ``correlation_id``, decodable by a
  downstream consumer (the OMN-14208 cross-boundary seam);
* the OMN-14743 seam regression (RED-proven both ways): fail-closed raise on a null
  ``event_type`` so nothing is emitted, and the emitted ``event_type`` MATCHES the key a
  type-scoped consumer routes on — so the delegation drop cannot recur;
* delivery policy — per-partition contiguous-prefix commit (HOLE 1), nack/redeliver,
  DLQ-on-exhaust, and no-silent-drop of an unmapped topic.

The handlers here are def-B (``handle(request: ModelX) -> ModelY``) and never import
``ModelEventEnvelope`` — the envelope boundary is entirely inside RuntimeDispatch.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4, uuid5

import pytest
from pydantic import BaseModel, ConfigDict

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.protocols.runtime.protocol_transport_consumer import (
    ProtocolTransportConsumer,
)
from omnibase_core.protocols.runtime.protocol_transport_producer import (
    ProtocolTransportProducer,
)
from omnibase_core.runtime.runtime_dispatch import DispatchRoute, RuntimeDispatch
from omnibase_core.runtime.runtime_envelope_router import (
    CAUSATION_ID_TAG,
    derive_event_type_from_topic,
)
from omnibase_core.runtime.transport import InMemoryBroker, InMemoryTransport

pytestmark = pytest.mark.asyncio

# --- topics -----------------------------------------------------------------
IN_TOPIC = "onex.cmd.omnitest.double.v1"
DONE_TOPIC = "onex.evt.omnitest.double-done.v1"
AUDIT_TOPIC = "onex.evt.omnitest.double-audited.v1"


# --- def-B payload models (pure domain types; NOT ModelEventEnvelope) -------
class ModelDoubleCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int


class ModelDoubled(BaseModel):
    model_config = ConfigDict(extra="forbid")
    doubled: int


class ModelDoubleAudited(BaseModel):
    model_config = ConfigDict(extra="forbid")
    original: int


# --- def-B handlers (handle(request) -> response; never touch the envelope) --
class DoublerHandler:
    async def handle(self, request: ModelDoubleCommand) -> ModelDoubled:
        return ModelDoubled(doubled=request.n * 2)


class FanoutHandler:
    """Returns an ordered fan-out sequence -> two distinct topics."""

    async def handle(
        self, request: ModelDoubleCommand
    ) -> Sequence[ModelDoubled | ModelDoubleAudited]:
        return [
            ModelDoubled(doubled=request.n * 2),
            ModelDoubleAudited(original=request.n),
        ]


class PoisonHandler:
    """Raises for the poison sentinel value, doubles otherwise (deterministic)."""

    POISON = 999

    async def handle(self, request: ModelDoubleCommand) -> ModelDoubled:
        if request.n == self.POISON:
            raise RuntimeError(f"poison input {request.n}")
        return ModelDoubled(doubled=request.n * 2)


class FlakyHandler:
    """Fails its first invocation, then succeeds (models a transient error)."""

    def __init__(self) -> None:
        self.calls = 0

    async def handle(self, request: ModelDoubleCommand) -> ModelDoubled:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("transient failure")
        return ModelDoubled(doubled=request.n * 2)


# --- fixtures / helpers -----------------------------------------------------
@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


@pytest.fixture
def producer(broker: InMemoryBroker) -> InMemoryTransport:
    return InMemoryTransport(broker=broker, group="producer")


def _consumer(
    broker: InMemoryBroker, *, group: str, topics: Sequence[str]
) -> InMemoryTransport:
    return InMemoryTransport(broker=broker, group=group, topics=topics)


async def _seed(
    producer: InMemoryTransport, topic: str, payload: BaseModel, *, correlation_id: UUID
) -> ModelEventEnvelope[BaseModel]:
    """Publish an enveloped input command; return the envelope for id assertions."""
    envelope: ModelEventEnvelope[BaseModel] = ModelEventEnvelope(
        payload=payload, correlation_id=correlation_id
    )
    await producer.send(
        topic, key=None, value=envelope.model_dump_json().encode("utf-8"), headers={}
    )
    return envelope


async def _drain_topic(
    broker: InMemoryBroker, topic: str
) -> list[ModelEventEnvelope[dict[str, object]]]:
    """Decode everything a downstream consumer would see on ``topic``."""
    reader = _consumer(broker, group=f"downstream-{topic}", topics=[topic])
    await reader.start()
    messages = await reader.poll(max_messages=100, timeout_ms=0)
    return [
        ModelEventEnvelope[dict[str, object]].model_validate_json(m.value)
        for m in messages
    ]


def _route(
    name: str,
    handler: object,
    published_events: dict[str, str],
    *,
    input_model_cls: type[BaseModel] | None = None,
) -> DispatchRoute:
    return DispatchRoute(
        name=name,
        handler=handler,  # type: ignore[arg-type]  # def-B handler satisfies ProtocolLocalRuntimeCallableTarget structurally
        published_events=published_events,
        input_model_cls=input_model_cls,
    )


# --- drift guard: local structural mirrors vs canonical protocols -----------
class TestCanonicalProtocolConformance:
    """The transports RuntimeDispatch consumes satisfy the CANONICAL protocols.

    RuntimeDispatch types its DI surface against private structural mirrors (declared
    locally to avoid a new ``protocols``-hub import edge, OMN-14340 ratchet). Those
    mirrors are subsets of the canonical protocols, so this binds the concrete
    transport to the CANONICAL types — if the canonical surface ever drops a method the
    runtime relies on, the transport loses it too and this fails."""

    async def test_injected_transport_satisfies_canonical_protocols(
        self, broker: InMemoryBroker
    ) -> None:
        transport = InMemoryTransport(broker=broker, group="g", topics=["t"])
        assert isinstance(transport, ProtocolTransportConsumer)
        assert isinstance(transport, ProtocolTransportProducer)
        # RuntimeDispatch accepts it as both consumer and producer (structural).
        RuntimeDispatch(consumer=transport, producer=transport, routing_map={})


# --- coercion ---------------------------------------------------------------
class TestCoercion:
    async def test_operation_match_annotation_driven_coercion(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """No input_model_cls: the ONE coercion validates the dict via the handler's
        own parameter annotation (OMN-8724), not a contract-declared event model."""
        corr = uuid4()
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=21), correlation_id=corr)
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_doubler", DoublerHandler(), {"Doubled": DONE_TOPIC}
        )  # input_model_cls omitted => operation_match path
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map={IN_TOPIC: route}
        )
        assert await rd.drain() == 1
        emitted = await _drain_topic(broker, DONE_TOPIC)
        assert [e.payload for e in emitted] == [{"doubled": 42}]

    async def test_payload_type_match_prevalidation(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        corr = uuid4()
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=5), correlation_id=corr)
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_doubler",
            DoublerHandler(),
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map={IN_TOPIC: route}
        )
        assert await rd.drain() == 1
        emitted = await _drain_topic(broker, DONE_TOPIC)
        assert [e.payload for e in emitted] == [{"doubled": 10}]


# --- fan-out ----------------------------------------------------------------
class TestFanout:
    async def test_multi_event_fanout_ordered_to_distinct_topics(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        corr = uuid4()
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=4), correlation_id=corr)
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_fanout",
            FanoutHandler(),
            {"Doubled": DONE_TOPIC, "DoubleAudited": AUDIT_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map={IN_TOPIC: route}
        )
        assert await rd.drain() == 1

        done = await _drain_topic(broker, DONE_TOPIC)
        audit = await _drain_topic(broker, AUDIT_TOPIC)
        assert [e.payload for e in done] == [{"doubled": 8}]
        assert [e.payload for e in audit] == [{"original": 4}]
        # Deterministic ids reflect fan-out order idx (0 -> Doubled, 1 -> DoubleAudited).
        assert done[0].envelope_id == uuid5(corr, "ModelDoubled:0")
        assert audit[0].envelope_id == uuid5(corr, "ModelDoubleAudited:1")


# --- golden chain (the OMN-14208 cross-boundary seam) -----------------------
class TestGoldenChain:
    async def test_every_emitted_envelope_has_non_null_event_type_and_correlation(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """publish input -> dispatch -> N events; assert each emitted envelope carries a
        NON-NULL event_type + propagated correlation + causation, and a downstream
        consumer can decode it. This is the seam the delegation drop broke (OMN-14743)."""
        corr = uuid4()
        inbound = await _seed(
            producer, IN_TOPIC, ModelDoubleCommand(n=10), correlation_id=corr
        )
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_fanout",
            FanoutHandler(),
            {"Doubled": DONE_TOPIC, "DoubleAudited": AUDIT_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map={IN_TOPIC: route}
        )
        await rd.drain()

        done = await _drain_topic(broker, DONE_TOPIC)
        audit = await _drain_topic(broker, AUDIT_TOPIC)
        for envelope in (*done, *audit):
            assert envelope.event_type, (
                "emitted event_type must be non-null (OMN-14743)"
            )
            assert envelope.correlation_id == corr
            assert envelope.metadata.tags[CAUSATION_ID_TAG] == str(inbound.envelope_id)
        # event_type is derived from the topic each event actually landed on.
        assert done[0].event_type == "omnitest.double-done"
        assert audit[0].event_type == "omnitest.double-audited"


# --- OMN-14743 seam regression (RED-proven) ---------------------------------
class TestOmn14743Seam:
    async def test_null_event_type_is_never_emitted_and_message_dlqd(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """RED-proof: route a handler's output to a NON-ONEX topic (event_type would
        derive to null). RuntimeDispatch must (a) emit NOTHING to that topic — the
        fail-closed guarantee — and (b) surface + DLQ the message, never silently commit
        it as the pre-fix swallow boundary did."""
        bad_topic = "legacy_non_onex_topic"
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=3), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_doubler",
            DoublerHandler(),
            {"Doubled": bad_topic},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={IN_TOPIC: route},
            max_retries=1,
        )
        await rd.drain()

        # (a) fail-closed: NOTHING emitted to the null-event_type topic.
        assert list(broker.records(bad_topic, 0)) == []
        # (b) not swallowed: the message is on the DLQ, and the offset advanced past it.
        assert len(broker.records(f"{IN_TOPIC}.dlq", 0)) == 1
        assert broker.committed_offset(IN_TOPIC, "node", 0) == 0

    async def test_emitted_event_type_matches_type_scoped_consumer_key(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """The delegation drop was: emitted event_type=null, so a type-scoped consumer
        (which routes on event_type derived from the topic) dropped it. Assert the
        emitted event_type EQUALS exactly that derived key, so routing cannot miss."""
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=2), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_doubler",
            DoublerHandler(),
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map={IN_TOPIC: route}
        )
        await rd.drain()

        emitted = await _drain_topic(broker, DONE_TOPIC)
        assert len(emitted) == 1
        consumer_routing_key = derive_event_type_from_topic(DONE_TOPIC)
        assert emitted[0].event_type == consumer_routing_key == "omnitest.double-done"


# --- delivery policy: HOLE 1 prefix-commit -----------------------------------
class TestPrefixCommit:
    async def test_redeliver_stops_the_partition_prefix_hole1(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """Three messages on one partition: m0 ok, m1 poison, m2 ok. In ONE poll cycle,
        only m0's offset may commit; committing m2 would advance the HWM past the
        uncommitted m1 and silently lose it (HOLE 1). Assert the prefix stops at m1 —
        committed offset is 0 (not 2) and m2 is NOT processed/emitted this round."""
        for n in (1, PoisonHandler.POISON, 3):
            await _seed(
                producer, IN_TOPIC, ModelDoubleCommand(n=n), correlation_id=uuid4()
            )
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_poison",
            PoisonHandler(),
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={IN_TOPIC: route},
            max_retries=5,  # m1 REDELIVERs (does not DLQ) within this single cycle
        )
        await consumer.start()
        await rd.run_once()

        # Only the contiguous prefix [m0] committed; the HWM did NOT jump past poison m1.
        assert broker.committed_offset(IN_TOPIC, "node", 0) == 0
        # m2 was never reached: exactly one output (from m0), not two.
        assert len(broker.records(DONE_TOPIC, 0)) == 1

    async def test_partitions_and_topics_commit_independently(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """A poison on one (topic,partition) group must not block another group's commit
        (grouping is per (topic, partition))."""
        other_in = "onex.cmd.omnitest.triple.v1"
        other_out = "onex.evt.omnitest.tripled.v1"
        await _seed(
            producer,
            IN_TOPIC,
            ModelDoubleCommand(n=PoisonHandler.POISON),
            correlation_id=uuid4(),
        )
        await _seed(producer, other_in, ModelDoubleCommand(n=7), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC, other_in])
        routes = {
            IN_TOPIC: _route(
                "poison",
                PoisonHandler(),
                {"Doubled": DONE_TOPIC},
                input_model_cls=ModelDoubleCommand,
            ),
            other_in: _route(
                "ok",
                DoublerHandler(),
                {"Doubled": other_out},
                input_model_cls=ModelDoubleCommand,
            ),
        }
        rd = RuntimeDispatch(
            consumer=consumer, producer=producer, routing_map=routes, max_retries=5
        )
        await consumer.start()
        await rd.run_once()

        # Poison topic: uncommitted (redelivered). Healthy topic: committed independently.
        assert broker.committed_offset(IN_TOPIC, "node", 0) == -1
        assert broker.committed_offset(other_in, "node", 0) == 0
        assert len(broker.records(other_out, 0)) == 1


# --- delivery policy: redeliver + DLQ ---------------------------------------
class TestRedeliverAndDlq:
    async def test_transient_failure_redelivers_then_succeeds(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        handler = FlakyHandler()
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=6), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_flaky",
            handler,
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={IN_TOPIC: route},
            max_retries=3,
        )
        await rd.drain()

        assert handler.calls == 2  # failed once, redelivered, then succeeded
        emitted = await _drain_topic(broker, DONE_TOPIC)
        assert [e.payload for e in emitted] == [{"doubled": 12}]
        assert broker.committed_offset(IN_TOPIC, "node", 0) == 0

    async def test_poison_message_dlqd_after_retries_exhausted(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        await _seed(
            producer,
            IN_TOPIC,
            ModelDoubleCommand(n=PoisonHandler.POISON),
            correlation_id=uuid4(),
        )
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        route = _route(
            "node_poison",
            PoisonHandler(),
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={IN_TOPIC: route},
            max_retries=1,
        )
        await rd.drain()

        assert list(broker.records(DONE_TOPIC, 0)) == []  # never terminalized
        assert len(broker.records(f"{IN_TOPIC}.dlq", 0)) == 1  # durable evidence
        assert broker.committed_offset(IN_TOPIC, "node", 0) == 0  # progress past it


# --- routing: no silent drop / boot checks ----------------------------------
class TestRouting:
    async def test_unmapped_topic_is_not_silently_dropped(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """A message on a topic with no route and no default_route must fail closed
        (surfaced + DLQ'd), never be silently committed."""
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=1), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={},  # IN_TOPIC unmapped
            max_retries=0,
        )
        await rd.drain()
        assert len(broker.records(f"{IN_TOPIC}.dlq", 0)) == 1

    async def test_default_route_handles_unmapped_topic(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        await _seed(producer, IN_TOPIC, ModelDoubleCommand(n=8), correlation_id=uuid4())
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        default = _route(
            "default",
            DoublerHandler(),
            {"Doubled": DONE_TOPIC},
            input_model_cls=ModelDoubleCommand,
        )
        rd = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={},
            default_route=default,
        )
        await rd.drain()
        emitted = await _drain_topic(broker, DONE_TOPIC)
        assert [e.payload for e in emitted] == [{"doubled": 16}]

    async def test_non_injective_published_events_fails_at_boot(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        consumer = _consumer(broker, group="node", topics=[IN_TOPIC])
        # Two distinct classes -> same topic violates injectivity (I4 boot check).
        bad_route = _route(
            "bad",
            FanoutHandler(),
            {"Doubled": DONE_TOPIC, "DoubleAudited": DONE_TOPIC},
        )
        with pytest.raises(ModelOnexError, match="injective"):
            RuntimeDispatch(
                consumer=consumer, producer=producer, routing_map={IN_TOPIC: bad_route}
            )
