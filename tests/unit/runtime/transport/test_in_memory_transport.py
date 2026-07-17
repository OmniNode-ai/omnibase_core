# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Focused unit tests for ``InMemoryTransport`` cursor edge cases (OMN-14720).

These exercise the Kafka-faithful per-``(topic, group, partition)`` monotonic
committed-offset cursor directly, including the plan's HOLE-1 out-of-order-commit
bug being *observable* in-memory, nack-then-repoll, restart redelivery, chaos
duplication, and per-partition isolation.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.protocols.runtime.protocol_transport_consumer import (
    ProtocolTransportConsumer,
)
from omnibase_core.protocols.runtime.protocol_transport_producer import (
    ProtocolTransportProducer,
)
from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker
from omnibase_core.runtime.transport.runtime_in_memory_transport import (
    InMemoryTransport,
)

TOPIC = "transport.inmemory-edge.v1"


def _consumer(
    broker: InMemoryBroker,
    *,
    group: str = "g",
    topics: Sequence[str] = (TOPIC,),
    chaos_duplicate: bool = False,
) -> InMemoryTransport:
    return InMemoryTransport(
        broker=broker, group=group, topics=topics, chaos_duplicate=chaos_duplicate
    )


async def _send_n(broker: InMemoryBroker, n: int, *, key: bytes | None = b"k") -> None:
    producer = InMemoryTransport(broker=broker, group="producer")
    for i in range(n):
        await producer.send(TOPIC, key=key, value=str(i).encode(), headers={})


# --------------------------------------------------------------------------- #
# Structural protocol satisfaction
# --------------------------------------------------------------------------- #


def test_in_memory_transport_satisfies_both_protocols() -> None:
    broker = InMemoryBroker()
    # mypy: the concrete class is assignable to each structural protocol.
    consumer: ProtocolTransportConsumer = InMemoryTransport(broker=broker)
    producer: ProtocolTransportProducer = InMemoryTransport(broker=broker)
    assert isinstance(consumer, ProtocolTransportConsumer)
    assert isinstance(producer, ProtocolTransportProducer)


# --------------------------------------------------------------------------- #
# HOLE 1 — out-of-order commit is observable in-memory
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_out_of_order_commit_defeats_earlier_redelivery_hole1() -> None:
    """Committing a LATER offset silently commits an earlier uncommitted one.

    This is the plan's HOLE-1 bug made visible in-memory: a buggy dispatch loop that
    processes offset 0 OK, fails offset 1 (should redeliver), but keeps going and
    commits offset 2 — the commit at offset 2 advances the HWM past offset 1, so the
    failed message is NOT redelivered on restart (silent loss). A correct runtime
    must stop the per-partition prefix at offset 1 and never commit offset 2.
    """
    broker = InMemoryBroker()
    await _send_n(broker, 3)  # single partition: offsets 0, 1, 2

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in batch] == [0, 1, 2]
    # Buggy loop: skip committing the "failed" offset 1, commit offset 2 anyway.
    await consumer.commit(batch[2])
    await consumer.close()

    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    # Offset 1 (the failed message) is silently gone — HOLE-1 is visible here.
    assert redelivered == []


@pytest.mark.asyncio
async def test_contiguous_prefix_commit_preserves_redelivery() -> None:
    """The correct pattern: commit only the contiguous prefix, redeliver the rest.

    Commit offset 0 (the contiguous successfully-terminalized prefix) and stop; on
    restart, offsets 1 and 2 are redelivered — the redelivery HOLE 1 destroys is
    preserved when the runtime does not commit past a failure.
    """
    broker = InMemoryBroker()
    await _send_n(broker, 3)

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.commit(batch[0])  # only the contiguous prefix
    await consumer.close()

    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    assert [m.offset for m in redelivered] == [1, 2]


# --------------------------------------------------------------------------- #
# commit-at-k commits all <= k (durable-cursor semantics)
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_commit_at_k_commits_all_leq_k() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 4)  # offsets 0..3 on one partition

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in batch] == [0, 1, 2, 3]
    # Commit offset 2 without ever committing 0 or 1.
    await consumer.commit(batch[2])
    await consumer.close()
    # Broker HWM proves all <= 2 committed.
    assert broker.committed_offset(TOPIC, "g", 0) == 2

    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    # Only offset 3 (> k) survives; 0, 1, 2 are all committed.
    assert [m.offset for m in redelivered] == [3]


@pytest.mark.asyncio
async def test_commit_high_water_mark_is_monotonic() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 3)

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.commit(batch[2])  # commit offset 2
    await consumer.commit(batch[0])  # a lower commit must NOT move the HWM back
    await consumer.close()
    assert broker.committed_offset(TOPIC, "g", 0) == 2

    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    assert redelivered == []


# --------------------------------------------------------------------------- #
# nack — re-expose from the offset
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_nack_then_repoll_redelivers_from_cursor() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 3)

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in batch] == [0, 1, 2]

    # nack the middle message: re-exposes it AND every later same-partition offset.
    await consumer.nack(batch[1])
    repoll = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    assert [m.offset for m in repoll] == [1, 2]


@pytest.mark.asyncio
async def test_nack_earliest_redelivers_whole_partition() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 3)

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.nack(batch[0])
    repoll = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    assert [m.offset for m in repoll] == [0, 1, 2]


# --------------------------------------------------------------------------- #
# in-flight / restart semantics
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_poll_marks_in_flight_but_does_not_remove() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 3)

    consumer = _consumer(broker)
    await consumer.start()
    first = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in first] == [0, 1, 2]
    # Same instance, no commit/nack: in-flight messages are NOT re-delivered.
    second = await consumer.poll(max_messages=10, timeout_ms=0)
    assert second == []
    await consumer.close()

    # Records were never removed: a restart (new instance, same group) redelivers all.
    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    assert [m.offset for m in redelivered] == [0, 1, 2]


@pytest.mark.asyncio
async def test_fresh_group_reads_from_beginning() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 2)
    consumer = _consumer(broker, group="brand-new")
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    assert [m.offset for m in batch] == [0, 1]


# --------------------------------------------------------------------------- #
# chaos / duplicate mode
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_chaos_mode_redelivers_committed_offset_exactly_once() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 1)

    consumer = _consumer(broker, chaos_duplicate=True)
    await consumer.start()
    first = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in first] == [0]

    await consumer.commit(first[0])  # commit schedules ONE chaos redelivery
    duplicate = await consumer.poll(max_messages=10, timeout_ms=0)
    assert [m.offset for m in duplicate] == [0]
    assert duplicate[0].value == first[0].value  # same committed message, redelivered

    await consumer.commit(duplicate[0])  # committing the duplicate does not re-arm it
    third = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    assert third == []  # delivered at most once more


@pytest.mark.asyncio
async def test_non_chaos_consumer_does_not_duplicate() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 1)

    consumer = _consumer(broker, chaos_duplicate=False)
    await consumer.start()
    first = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.commit(first[0])
    again = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    assert again == []


# --------------------------------------------------------------------------- #
# partitioning
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_per_partition_isolation_under_commit() -> None:
    """Committing one partition must not affect another partition's redelivery."""
    broker = InMemoryBroker(num_partitions=2)
    producer = InMemoryTransport(broker=broker, group="producer")
    # Unkeyed => deterministic round-robin: sends land p0, p1, p0, p1.
    for i in range(4):
        await producer.send(TOPIC, key=None, value=str(i).encode(), headers={})

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    p0 = [m for m in batch if m.partition == 0]
    p1 = [m for m in batch if m.partition == 1]
    assert [m.offset for m in p0] == [0, 1]
    assert [m.offset for m in p1] == [0, 1]

    # Commit the whole of partition 0 only.
    await consumer.commit(max(p0, key=lambda m: m.offset))
    await consumer.close()

    restart = _consumer(broker)
    await restart.start()
    redelivered = await restart.poll(max_messages=10, timeout_ms=0)
    await restart.close()
    # Partition 0 fully committed; partition 1 fully redelivered.
    assert {m.partition for m in redelivered} == {1}
    assert sorted(m.offset for m in redelivered) == [0, 1]


@pytest.mark.asyncio
async def test_keyed_partition_assignment_is_stable() -> None:
    broker = InMemoryBroker(num_partitions=3)
    producer = InMemoryTransport(broker=broker, group="producer")
    for _ in range(5):
        await producer.send(TOPIC, key=b"stable-key", value=b"x", headers={})

    consumer = _consumer(broker)
    await consumer.start()
    batch = await consumer.poll(max_messages=10, timeout_ms=0)
    await consumer.close()
    # Same key => all on one partition, contiguous offsets.
    assert len({m.partition for m in batch}) == 1
    assert [m.offset for m in batch] == [0, 1, 2, 3, 4]


# --------------------------------------------------------------------------- #
# fail-fast guards
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_poll_before_start_raises() -> None:
    broker = InMemoryBroker()
    consumer = _consumer(broker)
    with pytest.raises(ModelOnexError):
        await consumer.poll(max_messages=1, timeout_ms=0)


@pytest.mark.asyncio
async def test_poll_zero_max_messages_raises() -> None:
    broker = InMemoryBroker()
    consumer = _consumer(broker)
    await consumer.start()
    with pytest.raises(ModelOnexError):
        await consumer.poll(max_messages=0, timeout_ms=0)
    await consumer.close()


def test_zero_partitions_rejected() -> None:
    with pytest.raises(ModelOnexError):
        InMemoryBroker(num_partitions=0)


@pytest.mark.asyncio
async def test_poll_respects_max_messages_bound() -> None:
    broker = InMemoryBroker()
    await _send_n(broker, 3)
    consumer = _consumer(broker)
    await consumer.start()
    first = await consumer.poll(max_messages=2, timeout_ms=0)
    assert [m.offset for m in first] == [0, 1]
    second = await consumer.poll(max_messages=2, timeout_ms=0)
    await consumer.close()
    assert [m.offset for m in second] == [2]
