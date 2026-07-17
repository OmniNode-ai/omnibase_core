# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Parametrized transport conformance suite (the substitutability oracle).

Net-new foundation for the single-runtime / transport-via-DI unification (epic
OMN-14717, ticket OMN-14720; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` section
(d.4)). This is the mechanism that licenses "in-memory golden chain ⇒ Kafka golden
chain": one suite of behavioural assertions runs against ANY transport
implementation and asserts identical observable Kafka semantics.

How to use it
-------------
The suite is a mixin of undecorated ``async def test_*`` methods that consume two
fixtures BY NAME — ``transport_producer`` (a ``ProtocolTransportProducer``) and
``transport_consumer_factory`` (``(*, group, topics) -> ProtocolTransportConsumer``).
A concrete subclass supplies both fixtures; each test then gets a *fresh*
environment (fresh in-memory broker / fresh Kafka topic) so offsets and committed
cursors do not bleed across tests.

The suite is deliberately kept free of pytest and of the ``protocols`` import hub:
the fixtures are typed ``Any`` here (the harness is transport-agnostic; the concrete
protocol binding is asserted in the subclass). Core parametrises it against
``InMemoryTransport`` (this repo, S2); infra (S3) subclasses the SAME suite with a
Kafka-backed environment, which is what proves the two transports substitutable::

    class TestKafkaTransportConformance(TransportConformanceSuite):
        pytestmark = pytest.mark.asyncio  # pytest.ini runs asyncio in STRICT mode

        @pytest.fixture
        def transport_producer(self) -> KafkaTransport: ...

        @pytest.fixture
        def transport_consumer_factory(self) -> Callable[..., KafkaTransport]: ...

The assertions encode the corrected Kafka semantics (plan HOLE 2), NOT SQS
per-message ack:

* ``poll`` returns messages in per-partition offset order;
* **commit at offset k commits ALL offsets <= k on that partition** (the corrected
  assertion — replaces Design B's wrong "advances past exactly one message");
* ``nack`` redelivers from the offset (the message + later same-partition offsets);
* uncommitted offsets are redelivered on restart (new consumer, same group);
* ``send`` is per-topic ordered and headers/keys/partition/offset round-trip.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

__all__ = ["CONFORMANCE_TOPIC", "TransportConformanceSuite"]

# A single topic is enough: every assertion is about per-partition offset behaviour,
# and messages with the same key land on the same partition on any transport. This is
# a SYNTHETIC test topic that never routes in production — deliberately NOT an
# ``onex.(cmd|evt|dlq).*`` name so it stays out of the canonical topic registry.
CONFORMANCE_TOPIC = "transport.conformance.v1"  # env-var-ok: fixed synthetic test topic, never env-configured


async def _drain(
    consumer: Any, *, max_polls: int = 10, max_messages: int = 64
) -> list[Any]:
    """Poll until an empty batch (or ``max_polls``), collecting every message."""
    collected: list[Any] = []
    for _ in range(max_polls):
        batch = await consumer.poll(max_messages=max_messages, timeout_ms=50)
        if not batch:
            break
        collected.extend(batch)
    return collected


class TransportConformanceSuite:
    """Shared behavioural conformance for any transport implementation.

    Subclasses MUST provide ``transport_producer`` and ``transport_consumer_factory``
    pytest fixtures. This base class is intentionally NOT named ``Test*`` so pytest
    does not collect it directly (``python_classes = ["Test*"]``); only the concrete
    subclass is collected, inheriting these methods.
    """

    async def test_poll_returns_messages_in_per_partition_offset_order(
        self, transport_producer: Any, transport_consumer_factory: Any
    ) -> None:
        # Same key => one partition => a clean per-partition ordering check.
        for i in range(4):
            await transport_producer.send(
                CONFORMANCE_TOPIC, key=b"order", value=str(i).encode(), headers={}
            )
        consumer = transport_consumer_factory(
            group="g-order", topics=[CONFORMANCE_TOPIC]
        )
        await consumer.start()
        messages = await _drain(consumer)
        await consumer.close()

        assert messages, "expected the produced messages to be polled"
        by_partition: dict[int, list[int]] = defaultdict(list)
        for message in messages:
            by_partition[message.partition].append(message.offset)
        for partition, offsets in by_partition.items():
            assert offsets == sorted(offsets), (
                f"partition {partition} offsets out of order: {offsets}"
            )
            # Contiguous within the partition (no gaps in delivery order).
            assert offsets == list(range(offsets[0], offsets[0] + len(offsets)))
        # Same key => single partition => strict send order preserved end-to-end.
        assert [m.value for m in messages] == [b"0", b"1", b"2", b"3"]

    async def test_commit_at_k_commits_all_leq_k_on_partition(
        self, transport_producer: Any, transport_consumer_factory: Any
    ) -> None:
        # THE corrected assertion (plan HOLE 2): committing offset k commits every
        # offset <= k on that partition, NOT just the one message.
        for i in range(3):
            await transport_producer.send(
                CONFORMANCE_TOPIC, key=b"commit", value=str(i).encode(), headers={}
            )
        first = transport_consumer_factory(group="g-commit", topics=[CONFORMANCE_TOPIC])
        await first.start()
        batch = await _drain(first)
        assert len(batch) == 3
        partition = batch[0].partition
        assert all(m.partition == partition for m in batch), "same key => 1 partition"
        base = min(m.offset for m in batch)
        middle = next(m for m in batch if m.offset == base + 1)

        # Commit ONLY the middle offset — never explicitly commit the first.
        await first.commit(middle)
        await first.close()

        # Restart: a new consumer on the same group resumes from the committed HWM.
        second = transport_consumer_factory(
            group="g-commit", topics=[CONFORMANCE_TOPIC]
        )
        await second.start()
        redelivered = await _drain(second)
        await second.close()

        redelivered_offsets = {m.offset for m in redelivered}
        # base and base+1 are BOTH committed by the single commit at base+1.
        assert base not in redelivered_offsets, (
            "commit at k must commit the earlier offset k-1 too (all <= k)"
        )
        assert (base + 1) not in redelivered_offsets
        # base+2 was never committed => still redelivered.
        assert redelivered_offsets == {base + 2}

    async def test_nack_redelivers_from_offset_including_later(
        self, transport_producer: Any, transport_consumer_factory: Any
    ) -> None:
        for i in range(3):
            await transport_producer.send(
                CONFORMANCE_TOPIC, key=b"nack", value=str(i).encode(), headers={}
            )
        consumer = transport_consumer_factory(
            group="g-nack", topics=[CONFORMANCE_TOPIC]
        )
        await consumer.start()
        batch = await _drain(consumer)
        assert len(batch) == 3
        base = min(m.offset for m in batch)
        target = next(m for m in batch if m.offset == base + 1)

        await consumer.nack(target)
        redelivered = await _drain(consumer)
        await consumer.close()

        offsets = sorted(m.offset for m in redelivered)
        # nack re-exposes the message AND every later same-partition offset.
        assert offsets == [base + 1, base + 2]

    async def test_uncommitted_offsets_redeliver_on_restart(
        self, transport_producer: Any, transport_consumer_factory: Any
    ) -> None:
        for i in range(3):
            await transport_producer.send(
                CONFORMANCE_TOPIC, key=b"restart", value=str(i).encode(), headers={}
            )
        first = transport_consumer_factory(
            group="g-restart", topics=[CONFORMANCE_TOPIC]
        )
        await first.start()
        batch = await _drain(first)
        assert len(batch) == 3
        base = min(m.offset for m in batch)
        earliest = next(m for m in batch if m.offset == base)

        # Commit only the earliest, then "crash" without committing the rest.
        await first.commit(earliest)
        await first.close()

        second = transport_consumer_factory(
            group="g-restart", topics=[CONFORMANCE_TOPIC]
        )
        await second.start()
        redelivered = await _drain(second)
        await second.close()

        offsets = sorted(m.offset for m in redelivered)
        assert offsets == [base + 1, base + 2]

    async def test_send_is_per_topic_ordered_and_roundtrips(
        self, transport_producer: Any, transport_consumer_factory: Any
    ) -> None:
        payloads = [
            (b"key-a", b"v0", {"h": b"0"}),
            (b"key-a", b"v1", {"h": b"1"}),
            (b"key-a", b"v2", {"h": b"2"}),
        ]
        for key, value, headers in payloads:
            await transport_producer.send(
                CONFORMANCE_TOPIC, key=key, value=value, headers=headers
            )
        consumer = transport_consumer_factory(
            group="g-roundtrip", topics=[CONFORMANCE_TOPIC]
        )
        await consumer.start()
        messages = await _drain(consumer)
        await consumer.close()

        assert len(messages) == 3
        # Same key => single partition => strict send order preserved.
        assert [m.value for m in messages] == [b"v0", b"v1", b"v2"]
        assert [m.key for m in messages] == [b"key-a", b"key-a", b"key-a"]
        assert [dict(m.headers) for m in messages] == [
            {"h": b"0"},
            {"h": b"1"},
            {"h": b"2"},
        ]
        # partition/offset round-trip: contiguous ascending offsets on one partition.
        base = messages[0].offset
        assert [m.offset for m in messages] == [base, base + 1, base + 2]
        assert all(m.topic == CONFORMANCE_TOPIC for m in messages)
        assert len({m.partition for m in messages}) == 1
