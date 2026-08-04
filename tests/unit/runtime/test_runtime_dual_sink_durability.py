# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""RED-first tests: RuntimeDispatch dual-sink terminal durability (OMN-15666).

The reusable runtime primitive: after handling exhausts, the primary DLQ is
attempted EXACTLY ONCE; only on its failure is the canonical quarantine sink
attempted; and if BOTH fail the source offset is NOT committed, so restart /
replay reprocesses the same source record.

Scenario table (the mock-first idempotent golden chain of the ticket's final
acceptance criterion) is declared once in :data:`SINK_SCENARIOS` and driven
through the same binding interface used by a real Kafka / durable-persistence
runner: ordered sink outcomes in, a recording commit adapter out. Nothing in
this module is coupled to the in-memory transport beyond the fixtures.

Joins two merged parent seams; every field path below is asserted verbatim, not
fuzzily searched (the r1-rejection defect class, Linear comment b1c09ed7):

* OMN-15665 (merged ``0ce53d68``) — ``ModelDeliveryContext`` is the authoritative
  source identity. The dual-sink request's ``source_*`` fields are that context's
  four fields, never a ``correlation_id`` alias and never a fresh ``uuid4()``.
* OMN-15667 (merged ``54d7bdf7``) — ``ModelQuarantineWirePayload`` (pre-ack, no
  broker coordinates by construction) and ``ModelQuarantineDispositionReceipt``
  (post-ack, sole carrier of quarantine coordinates).

Public Core name/field authority for the net-new surfaces: Linear comment
``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)
from omnibase_core.models.event_bus.model_primary_dlq_wire_payload import (
    ModelPrimaryDlqWirePayload,
)
from omnibase_core.models.event_bus.model_quarantine_wire_payload import (
    ModelQuarantineWirePayload,
)
from omnibase_core.models.event_bus.model_transport_publish_acknowledgement import (
    ModelTransportPublishAcknowledgement,
)
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope
from omnibase_core.models.runtime.model_delivery_context import ModelDeliveryContext
from omnibase_core.models.runtime.model_primary_dlq_disposition_receipt import (
    ModelPrimaryDlqDispositionReceipt,
)
from omnibase_core.models.runtime.model_quarantine_disposition_receipt import (
    ModelQuarantineDispositionReceipt,
)
from omnibase_core.models.runtime.model_terminal_disposition_request import (
    ModelTerminalDispositionRequest,
)
from omnibase_core.protocols.runtime.protocol_acknowledging_publish import (
    ProtocolAcknowledgingPublish,
)
from omnibase_core.protocols.runtime.protocol_terminal_disposition_adapter import (
    ProtocolTerminalDispositionAdapter,
)
from omnibase_core.protocols.runtime.protocol_terminal_disposition_store import (
    ProtocolTerminalDispositionStore,
)
from omnibase_core.protocols.runtime.protocol_transport_publish_acknowledgement import (
    ProtocolTransportPublishAcknowledgement,
)
from omnibase_core.runtime.runtime_dispatch import DispatchRoute, RuntimeDispatch
from omnibase_core.runtime.runtime_dual_sink import (
    ModelTerminalDispositionReceipt,
    build_terminal_disposition_request,
    execute_terminal_disposition_once,
    resolve_terminal_disposition,
)
from omnibase_core.runtime.runtime_dual_sink_failure import DualPublishFailureError
from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
from omnibase_core.runtime.transport.runtime_in_memory_transport import (
    InMemoryTransport,
)

pytestmark = pytest.mark.asyncio

IN_TOPIC = "onex.cmd.omnitest.dualsink.v1"
OUT_TOPIC = "onex.evt.omnitest.dualsink-echoed.v1"
PRIMARY_DLQ_TOPIC = "onex.cmd.omnitest.dualsink.v1.dlq"
QUARANTINE_TOPIC = "onex.dlq.quarantine.v1"


# --- the frozen scenario table (mock-first; reusable unchanged on real Kafka) ---


@dataclass(frozen=True)
class SinkScenario:
    """One ordered sink-outcome row of the golden chain."""

    scenario_id: str
    primary_ok: bool
    quarantine_ok: bool
    expect_quarantine_attempted: bool
    expect_commit: bool
    expect_receipt_type: type[BaseModel] | None


SINK_SCENARIOS: tuple[SinkScenario, ...] = (
    SinkScenario(
        scenario_id="primary-ack",
        primary_ok=True,
        quarantine_ok=True,
        expect_quarantine_attempted=False,
        expect_commit=True,
        expect_receipt_type=ModelPrimaryDlqDispositionReceipt,
    ),
    SinkScenario(
        scenario_id="fallback-ack",
        primary_ok=False,
        quarantine_ok=True,
        expect_quarantine_attempted=True,
        expect_commit=True,
        expect_receipt_type=ModelQuarantineDispositionReceipt,
    ),
    SinkScenario(
        scenario_id="dual-failure-no-commit",
        primary_ok=False,
        quarantine_ok=False,
        expect_quarantine_attempted=True,
        expect_commit=False,
        expect_receipt_type=None,
    ),
)


class PublishRefused(RuntimeError):
    """Deterministic sink failure injected by the scenario table."""


@dataclass
class RecordingSink:
    """Ordered, recording publish binding — the ONE interface mock and real share.

    ``publish`` has exactly the shape a real acknowledging Kafka producer exposes:
    ``(topic, key, value, headers) -> ModelTransportPublishAcknowledgement``. A
    real runner swaps this object out; the scenario table and every assertion
    below stay byte-identical.
    """

    ok_topics: frozenset[str]
    partition: int = 7
    base_offset: int = 400
    calls: list[tuple[str, bytes | None, bytes, tuple[tuple[str, bytes], ...]]] = field(
        default_factory=list
    )

    async def publish(
        self,
        *,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Sequence[tuple[str, bytes]],
    ) -> ModelTransportPublishAcknowledgement:
        self.calls.append((topic, key, value, tuple(headers)))
        if topic not in self.ok_topics:
            raise PublishRefused(f"sink refused publish to {topic}")
        return ModelTransportPublishAcknowledgement(
            topic=topic,
            partition=self.partition,
            offset=self.base_offset + len(self.calls),
        )

    def topics_called(self) -> list[str]:
        return [call[0] for call in self.calls]


def _sink_for(scenario: SinkScenario) -> RecordingSink:
    ok: set[str] = set()
    if scenario.primary_ok:
        ok.add(PRIMARY_DLQ_TOPIC)
    if scenario.quarantine_ok:
        ok.add(QUARANTINE_TOPIC)
    return RecordingSink(ok_topics=frozenset(ok))


SOURCE_KEY = b"source-key-bytes"
SOURCE_VALUE_ENVELOPE_ID = UUID("11111111-2222-3333-4444-555555555555")
SOURCE_HEADERS: tuple[tuple[str, bytes], ...] = (
    ("trace", b"\x01\x02"),
    ("trace", b"\x03\x04"),  # duplicate name, MUST survive in order
    ("origin", b"gw"),
)


SOURCE_CORRELATION_ID = UUID("99999999-8888-7777-6666-555555555555")


def _build_source_value() -> bytes:
    envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
        payload={"n": 1},
        correlation_id=SOURCE_CORRELATION_ID,
        envelope_id=SOURCE_VALUE_ENVELOPE_ID,
    )
    return envelope.model_dump_json().encode("utf-8")


# Computed ONCE. ModelEventEnvelope stamps a wall-clock field, so rebuilding it
# per call would make "the published bytes equal the source bytes" a vacuous
# comparison of two different byte strings.
_SOURCE_VALUE: bytes = _build_source_value()


def _source_value() -> bytes:
    """The one deterministic source-record byte string used by every assertion."""
    return _SOURCE_VALUE


def _context(*, partition: int = 3, offset: int = 42) -> ModelDeliveryContext:
    return ModelDeliveryContext(
        envelope_id=SOURCE_VALUE_ENVELOPE_ID,
        topic=IN_TOPIC,
        partition=partition,
        offset=offset,
    )


def _failure() -> ModelDeliveryFailureEvidence:
    return ModelDeliveryFailureEvidence(
        stage="handler_invoke",
        error_type="ModelOnexError",
        error_message="handler exhausted its retry budget",
        retryable=False,
    )


def _request(**overrides: object) -> ModelTerminalDispositionRequest:
    kwargs: dict[str, object] = {
        "context": _context(),
        "primary_dlq_topic": PRIMARY_DLQ_TOPIC,
        "quarantine_topic": QUARANTINE_TOPIC,
        "source_key": SOURCE_KEY,
        "source_value": _source_value(),
        "source_headers": SOURCE_HEADERS,
        "source_failure": _failure(),
    }
    kwargs.update(overrides)
    return build_terminal_disposition_request(**kwargs)  # type: ignore[arg-type]


# --- AC 1: the disposition input preserves the authoritative source identity ---


class TestDispositionInputIdentity:
    async def test_request_carries_exact_source_identity_and_intent_topic(self) -> None:
        request = _request()
        assert request.source_envelope_id == SOURCE_VALUE_ENVELOPE_ID
        assert request.source_topic == IN_TOPIC
        assert request.source_partition == 3
        assert request.source_offset == 42
        assert request.primary_dlq_topic == PRIMARY_DLQ_TOPIC
        assert request.quarantine_topic == QUARANTINE_TOPIC
        assert request.source_failure == _failure()

    async def test_source_envelope_id_is_not_a_correlation_id_or_fresh_uuid(
        self,
    ) -> None:
        """The wire correlation_id and a fresh uuid4() are both REJECTED aliases."""
        raw = json.loads(_source_value())
        correlation_id = raw.get("correlation_id")
        assert correlation_id is not None
        assert UUID(str(correlation_id)) != SOURCE_VALUE_ENVELOPE_ID
        first = _request().source_envelope_id
        second = _request().source_envelope_id
        assert first == second == SOURCE_VALUE_ENVELOPE_ID

    async def test_request_is_frozen_and_forbids_extra(self) -> None:
        request = _request()
        with pytest.raises(ValidationError):
            ModelTerminalDispositionRequest(**request.model_dump(), schema_version="v1")  # type: ignore[arg-type]

    async def test_source_bytes_and_ordered_duplicate_headers_survive_verbatim(
        self,
    ) -> None:
        request = _request()
        assert base64.b64decode(request.source_key_b64) == SOURCE_KEY
        assert base64.b64decode(request.source_value_b64) == _source_value()
        assert request.source_headers_b64 == tuple(
            (name, base64.b64encode(value).decode("ascii"))
            for name, value in SOURCE_HEADERS
        )
        # duplicate header name preserved, in order — never collapsed to a mapping
        assert [name for name, _ in request.source_headers_b64] == [
            "trace",
            "trace",
            "origin",
        ]


# --- AC 2/3/4/5: ordering, ack-gating, and the dual-failure no-commit rule ---


class TestDualSinkOrdering:
    @pytest.mark.parametrize(
        "scenario",
        SINK_SCENARIOS,
        ids=lambda s: s.scenario_id,  # type: ignore[misc]
    )
    async def test_scenario_table(self, scenario: SinkScenario) -> None:
        sink = _sink_for(scenario)
        request = _request()

        if scenario.expect_receipt_type is None:
            with pytest.raises(DualPublishFailureError) as excinfo:
                await resolve_terminal_disposition(
                    request=request, publish=sink.publish
                )
            # AC 5: the observable result NAMES BOTH failures
            assert isinstance(
                excinfo.value.primary_failure, ModelDeliveryFailureEvidence
            )
            assert isinstance(
                excinfo.value.quarantine_failure, ModelDeliveryFailureEvidence
            )
            assert excinfo.value.primary_failure.stage == "primary_dlq_publish"
            assert excinfo.value.quarantine_failure.stage == "quarantine_publish"
            assert excinfo.value.primary_failure.error_type == "PublishRefused"
            assert excinfo.value.quarantine_failure.error_type == "PublishRefused"
        else:
            receipt = await resolve_terminal_disposition(
                request=request, publish=sink.publish
            )
            assert type(receipt) is scenario.expect_receipt_type

        # AC 2: primary attempted EXACTLY ONCE, and always first.
        assert sink.topics_called().count(PRIMARY_DLQ_TOPIC) == 1
        assert sink.topics_called()[0] == PRIMARY_DLQ_TOPIC
        # AC 3: quarantine is NEVER called when the primary was acknowledged.
        assert (
            QUARANTINE_TOPIC in sink.topics_called()
        ) is scenario.expect_quarantine_attempted

    async def test_primary_ack_receipt_records_broker_returned_coordinates(
        self,
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[0])
        receipt = await resolve_terminal_disposition(
            request=_request(), publish=sink.publish
        )
        assert isinstance(receipt, ModelPrimaryDlqDispositionReceipt)
        # exact field paths — broker's ack, not the intent
        assert receipt.primary_dlq_topic == PRIMARY_DLQ_TOPIC
        assert receipt.primary_dlq_partition == sink.partition
        assert receipt.primary_dlq_offset == sink.base_offset + 1
        # the published record IS the exact validated pre-ack payload
        assert isinstance(receipt.primary_dlq_payload, ModelPrimaryDlqWirePayload)
        published = json.loads(sink.calls[0][2])
        assert published == receipt.primary_dlq_payload.model_dump(mode="json")

    async def test_fallback_receipt_records_primary_failure_and_quarantine_coords(
        self,
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[1])
        receipt = await resolve_terminal_disposition(
            request=_request(), publish=sink.publish
        )
        assert isinstance(receipt, ModelQuarantineDispositionReceipt)
        assert receipt.quarantine_topic == QUARANTINE_TOPIC
        assert receipt.quarantine_partition == sink.partition
        assert receipt.quarantine_offset == sink.base_offset + 2
        payload = receipt.quarantine_payload
        assert isinstance(payload, ModelQuarantineWirePayload)
        # OMN-15667 seam: primary failure is carried on the quarantine payload
        assert payload.primary_dlq_error_type == "PublishRefused"
        assert PRIMARY_DLQ_TOPIC in payload.primary_dlq_error_message
        assert payload.source_failure.stage == "primary_dlq_publish"
        # source tuple verbatim from the delivery context
        assert payload.source_envelope_id == SOURCE_VALUE_ENVELOPE_ID
        assert payload.source_topic == IN_TOPIC
        assert payload.source_partition == 3
        assert payload.source_offset == 42
        assert base64.b64decode(payload.source_value_b64) == _source_value()
        published = json.loads(sink.calls[1][2])
        assert published == payload.model_dump(mode="json")

    async def test_quarantine_wire_payload_has_no_broker_coordinates(self) -> None:
        """OMN-15667 causal invariant survives the join (r1 defect #1)."""
        forbidden = {"quarantine_topic", "quarantine_partition", "quarantine_offset"}
        assert not forbidden & set(ModelQuarantineWirePayload.model_fields)
        sink = _sink_for(SINK_SCENARIOS[1])
        await resolve_terminal_disposition(request=_request(), publish=sink.publish)
        assert not forbidden & set(json.loads(sink.calls[1][2]))

    async def test_no_commit_gate_before_acknowledgement(self) -> None:
        """AC 6: an unacknowledged publish future never yields a receipt."""

        async def never_acks(
            *,
            topic: str,
            key: bytes | None,
            value: bytes,
            headers: Sequence[tuple[str, bytes]],
        ) -> ModelTransportPublishAcknowledgement:
            raise PublishRefused("broker never acknowledged")

        with pytest.raises(DualPublishFailureError):
            await resolve_terminal_disposition(request=_request(), publish=never_acks)


# --- AC 7: replay after ambiguous death yields ONE terminal disposition ---


@dataclass
class RecordingDispositionStore:
    """Idempotent terminal-disposition store keyed by the exact source identity."""

    saved: dict[tuple[UUID, str, int, int], ModelTerminalDispositionReceipt] = field(
        default_factory=dict
    )
    loads: int = 0

    @staticmethod
    def _key(context: ModelDeliveryContext) -> tuple[UUID, str, int, int]:
        return (context.envelope_id, context.topic, context.partition, context.offset)

    async def load(
        self, context: ModelDeliveryContext
    ) -> ModelTerminalDispositionReceipt | None:
        self.loads += 1
        return self.saved.get(self._key(context))

    async def save(
        self, context: ModelDeliveryContext, receipt: ModelTerminalDispositionReceipt
    ) -> None:
        self.saved[self._key(context)] = receipt


class TestIdempotentReplay:
    async def test_replay_of_same_source_identity_publishes_once(self) -> None:
        sink = _sink_for(SINK_SCENARIOS[0])
        store = RecordingDispositionStore()
        context = _context()
        first = await execute_terminal_disposition_once(
            context=context,
            request=_request(),
            publish=sink.publish,
            store=store,
        )
        second = await execute_terminal_disposition_once(
            context=context,
            request=_request(),
            publish=sink.publish,
            store=store,
        )
        assert first == second
        assert len(store.saved) == 1
        assert len(sink.calls) == 1, "replay must not re-publish a terminal disposition"

    async def test_distinct_source_offset_is_a_distinct_terminal_disposition(
        self,
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[0])
        store = RecordingDispositionStore()
        await execute_terminal_disposition_once(
            context=_context(offset=42),
            request=_request(context=_context(offset=42)),
            publish=sink.publish,
            store=store,
        )
        await execute_terminal_disposition_once(
            context=_context(offset=43),
            request=_request(context=_context(offset=43)),
            publish=sink.publish,
            store=store,
        )
        assert len(store.saved) == 2
        assert len(sink.calls) == 2


# --- structural protocol conformance (the public seams) ---


class TestProtocolConformance:
    async def test_acknowledgement_satisfies_its_structural_protocol(self) -> None:
        ack = ModelTransportPublishAcknowledgement(
            topic=PRIMARY_DLQ_TOPIC, partition=0, offset=0
        )
        typed: ProtocolTransportPublishAcknowledgement = ack
        assert isinstance(typed, ProtocolTransportPublishAcknowledgement)

    async def test_acknowledgement_rejects_negative_broker_coordinates(self) -> None:
        for bad in ({"partition": -1, "offset": 0}, {"partition": 0, "offset": -1}):
            with pytest.raises(ValidationError):
                ModelTransportPublishAcknowledgement(topic="t", **bad)  # type: ignore[arg-type]

    async def test_recording_sink_satisfies_the_canonical_publish_protocol(
        self,
    ) -> None:
        """Mirror-drift guard: runtime_dual_sink declares a PRIVATE subset mirror of
        this protocol to avoid a protocols-hub import edge (OMN-14340). Binding the
        concrete sink to the CANONICAL type here fails if the mirror ever drifts."""
        sink = _sink_for(SINK_SCENARIOS[0])
        typed: ProtocolAcknowledgingPublish[ModelTransportPublishAcknowledgement] = (
            sink.publish
        )
        ack = await typed(topic=PRIMARY_DLQ_TOPIC, key=None, value=b"{}", headers=())
        assert isinstance(ack, ModelTransportPublishAcknowledgement)

    async def test_recording_store_satisfies_the_canonical_store_protocol(
        self,
    ) -> None:
        """Same mirror-drift guard for the disposition store."""
        store = RecordingDispositionStore()
        typed: ProtocolTerminalDispositionStore[
            ModelDeliveryContext, ModelTerminalDispositionReceipt
        ] = store
        assert isinstance(typed, ProtocolTerminalDispositionStore)

    async def test_dual_sink_adapter_satisfies_terminal_disposition_protocol(
        self,
    ) -> None:
        class _Adapter:
            async def execute_once(
                self,
                context: ModelDeliveryContext,
                request: ModelTerminalDispositionRequest,
                /,
            ) -> ModelPrimaryDlqDispositionReceipt:
                raise NotImplementedError

        adapter: ProtocolTerminalDispositionAdapter[
            ModelDeliveryContext,
            ModelTerminalDispositionRequest,
            ModelPrimaryDlqDispositionReceipt,
        ] = _Adapter()
        assert isinstance(adapter, ProtocolTerminalDispositionAdapter)


# --- the CROSS-BOUNDARY join: RuntimeDispatch drives the actual seam ---


class ModelEcho(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int


class ModelEchoed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    n: int


class ExplodingHandler:
    """def-B handler that always fails, so every message exhausts to terminal."""

    async def handle(self, request: ModelEcho) -> ModelEchoed:
        raise RuntimeError("handler always fails (drives the terminal path)")


class DualSinkAdapter:
    """Composition-root adapter: binds the sink + store into the runtime seam."""

    def __init__(self, sink: RecordingSink, store: RecordingDispositionStore) -> None:
        self._sink = sink
        self._store = store
        self.contexts: list[ModelDeliveryContext] = []

    async def execute_once(
        self,
        context: ModelDeliveryContext,
        request: ModelTerminalDispositionRequest,
        /,
    ) -> ModelTerminalDispositionReceipt:
        self.contexts.append(context)
        return await execute_terminal_disposition_once(
            context=context,
            request=request,
            publish=self._sink.publish,
            store=self._store,
        )


@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()


@pytest.fixture
def producer(broker: InMemoryBroker) -> InMemoryTransport:
    return InMemoryTransport(broker=broker, group="producer")


def _route() -> DispatchRoute:
    return DispatchRoute(
        name="echo",
        handler=ExplodingHandler(),  # type: ignore[arg-type]
        published_events={"ModelEchoed": OUT_TOPIC},
        input_model_cls=ModelEcho,
    )


async def _seed(producer: InMemoryTransport, *, envelope_id: UUID) -> None:
    envelope: ModelEventEnvelope[object] = ModelEventEnvelope(
        payload=ModelEcho(n=1), correlation_id=uuid4(), envelope_id=envelope_id
    )
    await producer.send(
        IN_TOPIC,
        key=SOURCE_KEY,
        value=envelope.model_dump_json().encode("utf-8"),
        headers={"origin": b"gw"},
    )


def _dispatch(
    broker: InMemoryBroker,
    producer: InMemoryTransport,
    *,
    adapter: DualSinkAdapter | None,
    group: str = "g",
) -> tuple[RuntimeDispatch, InMemoryTransport]:
    consumer = InMemoryTransport(broker=broker, group=group, topics=[IN_TOPIC])
    kwargs: dict[str, object] = {}
    if adapter is not None:
        kwargs["terminal_disposition_adapter"] = adapter
        kwargs["quarantine_topic_resolver"] = lambda _topic: QUARANTINE_TOPIC
    dispatch = RuntimeDispatch(
        consumer=consumer,
        producer=producer,
        routing_map={IN_TOPIC: _route()},
        max_retries=0,
        dlq_topic_resolver=lambda _topic: PRIMARY_DLQ_TOPIC,
        **kwargs,  # type: ignore[arg-type]
    )
    return dispatch, consumer


async def _started(
    broker: InMemoryBroker,
    producer: InMemoryTransport,
    *,
    adapter: DualSinkAdapter | None,
) -> RuntimeDispatch:
    dispatch, consumer = _dispatch(broker, producer, adapter=adapter)
    await consumer.start()
    return dispatch


class TestRuntimeDispatchDualSinkJoin:
    async def test_constructor_still_works_without_the_new_kwargs(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """No repeat of the 2026-08-02 CORE-PASS / CROSS-REPO-FAIL defect."""
        dispatch, _ = _dispatch(broker, producer, adapter=None)
        assert dispatch.dual_sink_enabled is False

    async def test_primary_ack_commits_exactly_once_and_skips_quarantine(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[0])
        store = RecordingDispositionStore()
        adapter = DualSinkAdapter(sink, store)
        dispatch = await _started(broker, producer, adapter=adapter)
        await _seed(producer, envelope_id=SOURCE_VALUE_ENVELOPE_ID)

        assert await dispatch.run_once() == 1
        assert sink.topics_called() == [PRIMARY_DLQ_TOPIC]
        # the runtime handed the adapter THIS record's real delivery context
        assert adapter.contexts[0].envelope_id == SOURCE_VALUE_ENVELOPE_ID
        assert adapter.contexts[0].topic == IN_TOPIC
        assert adapter.contexts[0].offset == 0
        # committed: a restart sees nothing left
        restart = InMemoryTransport(broker=broker, group="g", topics=[IN_TOPIC])
        await restart.start()
        assert await restart.poll(max_messages=8, timeout_ms=0) == []

    async def test_dual_failure_does_not_commit_and_replay_reprocesses(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[2])
        store = RecordingDispositionStore()
        adapter = DualSinkAdapter(sink, store)
        dispatch = await _started(broker, producer, adapter=adapter)
        await _seed(producer, envelope_id=SOURCE_VALUE_ENVELOPE_ID)

        assert await dispatch.run_once() == 1
        assert sink.topics_called() == [PRIMARY_DLQ_TOPIC, QUARANTINE_TOPIC]
        assert store.saved == {}
        # AC 5: NOT committed — a restart redelivers the SAME source record
        restart = InMemoryTransport(broker=broker, group="g", topics=[IN_TOPIC])
        await restart.start()
        redelivered = await restart.poll(max_messages=8, timeout_ms=0)
        assert [m.offset for m in redelivered] == [0]

    async def test_fallback_commits_and_records_quarantine_receipt(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[1])
        store = RecordingDispositionStore()
        adapter = DualSinkAdapter(sink, store)
        dispatch = await _started(broker, producer, adapter=adapter)
        await _seed(producer, envelope_id=SOURCE_VALUE_ENVELOPE_ID)

        assert await dispatch.run_once() == 1
        assert sink.topics_called() == [PRIMARY_DLQ_TOPIC, QUARANTINE_TOPIC]
        (receipt,) = store.saved.values()
        assert isinstance(receipt, ModelQuarantineDispositionReceipt)
        assert receipt.quarantine_payload.source_envelope_id == (
            SOURCE_VALUE_ENVELOPE_ID
        )
        restart = InMemoryTransport(broker=broker, group="g", topics=[IN_TOPIC])
        await restart.start()
        assert await restart.poll(max_messages=8, timeout_ms=0) == []

    async def test_untruthful_identity_never_enters_the_dual_sink_path(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        """A record with no wire envelope_id can key nothing — never fabricate one."""
        sink = _sink_for(SINK_SCENARIOS[0])
        adapter = DualSinkAdapter(sink, RecordingDispositionStore())
        dispatch = await _started(broker, producer, adapter=adapter)
        await producer.send(
            IN_TOPIC, key=None, value=b'{"payload": {"n": 1}}', headers={}
        )
        await dispatch.run_once()
        assert adapter.contexts == []
        assert sink.calls == []


# --- CodeRabbit-found regressions (PR #1546 review) --------------------------


class StoreBoom(RuntimeError):
    """Raw backend failure from an injected durable disposition store."""


@dataclass
class ExplodingStore:
    """Durable store whose backend raises raw, untyped exceptions."""

    fail_on: str

    async def load(
        self, context: ModelDeliveryContext
    ) -> ModelTerminalDispositionReceipt | None:
        if self.fail_on == "load":
            raise StoreBoom("backend connection reset during load")
        return None

    async def save(
        self, context: ModelDeliveryContext, receipt: ModelTerminalDispositionReceipt
    ) -> None:
        if self.fail_on == "save":
            raise StoreBoom("backend timeout during save")


class TestStoreFailuresAreTypedAndNonCommittable:
    """A raw store exception must surface as ModelOnexError, never untyped."""

    @pytest.mark.parametrize("fail_on", ["load", "save"])
    async def test_store_failure_is_wrapped_in_model_onex_error(
        self, fail_on: str
    ) -> None:
        sink = _sink_for(SINK_SCENARIOS[0])
        with pytest.raises(ModelOnexError) as excinfo:
            await execute_terminal_disposition_once(
                context=_context(),
                request=_request(),
                publish=sink.publish,
                store=ExplodingStore(fail_on=fail_on),  # type: ignore[arg-type]
            )
        assert not isinstance(excinfo.value, DualPublishFailureError)
        assert fail_on in str(excinfo.value)
        # the authoritative source identity is named in the typed error
        assert str(SOURCE_VALUE_ENVELOPE_ID) in str(excinfo.value)

    async def test_store_load_failure_never_publishes(self) -> None:
        """An unreadable store must not be treated as 'no prior disposition'."""
        sink = _sink_for(SINK_SCENARIOS[0])
        with pytest.raises(ModelOnexError):
            await execute_terminal_disposition_once(
                context=_context(),
                request=_request(),
                publish=sink.publish,
                store=ExplodingStore(fail_on="load"),  # type: ignore[arg-type]
            )
        assert sink.calls == []


class ExplodingAdapter:
    """Terminal-disposition adapter that fails with something OTHER than
    DualPublishFailureError (the store-I/O class)."""

    def __init__(self) -> None:
        self.calls = 0

    async def execute_once(
        self,
        context: ModelDeliveryContext,
        request: ModelTerminalDispositionRequest,
        /,
    ) -> ModelTerminalDispositionReceipt:
        self.calls += 1
        raise StoreBoom("durable store unavailable")


class TestUnexpectedAdapterFailureDoesNotAbortThePollCycle:
    """run_once must survive an unexpected adapter failure: the failing record
    stays uncommitted, but earlier successes and later partitions are unaffected."""

    async def test_unexpected_adapter_failure_leaves_record_uncommitted(
        self, broker: InMemoryBroker, producer: InMemoryTransport
    ) -> None:
        adapter = ExplodingAdapter()
        consumer = InMemoryTransport(broker=broker, group="g", topics=[IN_TOPIC])
        dispatch = RuntimeDispatch(
            consumer=consumer,
            producer=producer,
            routing_map={IN_TOPIC: _route()},
            max_retries=0,
            dlq_topic_resolver=lambda _topic: PRIMARY_DLQ_TOPIC,
            terminal_disposition_adapter=adapter,  # type: ignore[arg-type]
            quarantine_topic_resolver=lambda _topic: QUARANTINE_TOPIC,
        )
        await consumer.start()
        await _seed(producer, envelope_id=SOURCE_VALUE_ENVELOPE_ID)

        # MUST NOT raise out of run_once — that would abort the whole poll cycle.
        assert await dispatch.run_once() == 1
        assert adapter.calls == 1

        # not committed: a restart redelivers the SAME source record
        restart = InMemoryTransport(broker=broker, group="g", topics=[IN_TOPIC])
        await restart.start()
        assert [m.offset for m in await restart.poll(max_messages=8, timeout_ms=0)] == [
            0
        ]
