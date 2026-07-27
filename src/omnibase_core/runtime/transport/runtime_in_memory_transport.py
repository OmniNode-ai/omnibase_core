# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""In-memory transport modelling Kafka's per-partition offset semantics.

Net-new foundation for the single-runtime / transport-via-DI unification (epic
OMN-14717, ticket OMN-14720; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` sections
(c)/(d.4)). A real, usable transport for tests and local runs — NOT test-only
scaffolding — that nothing in production wires yet, so it is fully reversible with
zero production behavior change.

Why Kafka semantics and not SQS (plan HOLE 2)
---------------------------------------------
A naive in-memory transport keyed by an individual ``delivery_id`` where
``commit(one)`` discards exactly that one message models SQS / per-message ack.
Under that model the plan's HOLE-1 out-of-order-commit bug is *invisible* in-memory
and only bites the real broker. This transport instead models Kafka's monotonic
per-``(topic, group, partition)`` committed-offset **cursor**:

* ``commit(msg)`` advances the committed high-water mark to ``msg.offset`` — thereby
  committing every earlier offset on that partition too. You cannot commit ``m3``
  while ``m2`` is uncommitted without also committing ``m2``. This is exactly what
  makes the HOLE-1 bug (committing a later offset defeats redelivery of an earlier
  failed one) observable in-memory.
* ``nack(msg)`` does NOT advance the cursor; it re-exposes ``msg`` and every later
  same-partition offset (mirrors a Kafka ``seek``).
* A restart (a NEW consumer instance on the same group) resumes from the committed
  offset, so every uncommitted offset is redelivered.
* Optional opt-in chaos/duplicate mode redelivers a committed offset once more so an
  idempotence-requiring golden chain must prove handler idempotence — stricter than a
  naive Kafka happy path.

Bracketed (NOT modelled here; only the configured broker escalation covers them):
partition rebalance/assignment, cross-broker replication/durability, consumer-group
coordination, idempotent-producer/txn dedup, wall-clock latency, real network
partitions.

Structural conformance
----------------------
``InMemoryTransport`` structurally satisfies both ``ProtocolTransportConsumer`` and
``ProtocolTransportProducer`` (proven in the unit tests, which assign it to those
protocol types and ``isinstance``-check it). It deliberately does NOT import those
protocols: ``commit`` / ``nack`` accept ``object`` (a supertype of the protocol's
``ProtocolTransportMessage`` parameter, so the impl stays contravariantly
compatible) and narrow to the concrete ``ModelTransportMessage`` this transport
itself yields from ``poll``. The parametrized conformance suite
(:mod:`omnibase_core.runtime.transport.runtime_transport_conformance`) asserts the
observable Kafka semantics against ANY transport, which is what licenses
"in-memory golden chain ⇒ Kafka golden chain".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_transport_message import ModelTransportMessage
from omnibase_core.runtime.transport.runtime_in_memory_broker import InMemoryBroker

__all__ = ["InMemoryTransport"]


class InMemoryTransport:
    """A single in-memory transport that is both consumer and producer.

    Consumer identity (``group`` + assigned ``topics``) is construction-time config
    supplied by the composition root — there is no runtime ``subscribe`` call,
    mirroring the pull-based protocol. Fetch position is *instance-local*: a new
    instance on the same ``group`` (a "restart") initialises each partition's
    position from the broker's committed offset, so uncommitted offsets redeliver.
    """

    def __init__(
        self,
        *,
        broker: InMemoryBroker,
        group: str = "onex.transport.inmemory",
        topics: Sequence[str] = (),
        chaos_duplicate: bool = False,
    ) -> None:
        self._broker = broker
        self._group = group
        self._topics: tuple[str, ...] = tuple(topics)
        self._chaos_duplicate = chaos_duplicate
        self._started = False
        # (topic, partition) -> next offset this instance will fetch.
        self._positions: dict[tuple[str, int], int] = {}
        # Committed offsets awaiting one extra chaos redelivery, in commit order.
        self._chaos_pending: list[ModelTransportMessage] = []
        # (topic, partition, offset) already chaos-redelivered (at most once each).
        self._chaos_seen: set[tuple[str, int, int]] = set()

    # -- consumer protocol -------------------------------------------------

    async def start(self) -> None:
        self._started = True

    async def close(self) -> None:
        self._started = False

    def _require_started(self) -> None:
        if not self._started:
            raise ModelOnexError(
                "InMemoryTransport consumer used before start()",
                error_code=EnumCoreErrorCode.INVALID_STATE,
            )

    def _position(self, topic: str, partition: int) -> int:
        """Instance-local fetch position, lazily seeded from the committed offset."""
        cursor = (topic, partition)
        if cursor not in self._positions:
            self._positions[cursor] = (
                self._broker.committed_offset(topic, self._group, partition) + 1
            )
        return self._positions[cursor]

    async def poll(
        self, *, max_messages: int, timeout_ms: int
    ) -> Sequence[ModelTransportMessage]:
        """Return up to ``max_messages`` messages at/after the fetch position.

        Polled messages are marked in-flight (the fetch position advances past
        them) but are NOT removed from the log — a ``nack`` or a restart re-exposes
        any that stay uncommitted. ``timeout_ms`` is ignored: the in-memory log
        never blocks, it returns whatever is currently available (possibly empty).
        Chaos-mode duplicates of already-committed offsets are drained first.
        """
        self._require_started()
        if max_messages < 1:
            raise ModelOnexError(
                f"max_messages must be a positive integer, got {max_messages}",
                error_code=EnumCoreErrorCode.INVALID_INPUT,
            )

        batch: list[ModelTransportMessage] = []

        # Chaos redeliveries of committed offsets come first (opt-in).
        while self._chaos_pending and len(batch) < max_messages:
            batch.append(self._chaos_pending.pop(0))

        # Fresh delivery from each assigned (topic, partition) in a deterministic
        # order. Ascending offset within a partition is guaranteed by the log.
        for topic in sorted(self._topics):
            for partition in range(self._broker.num_partitions):
                if len(batch) >= max_messages:
                    break
                log = self._broker.records(topic, partition)
                position = self._position(topic, partition)
                while position < len(log) and len(batch) < max_messages:
                    batch.append(log[position])
                    position += 1
                self._positions[(topic, partition)] = position
        return batch

    async def commit(self, message: object) -> None:
        """Advance the partition high-water mark to ``message`` (commits all <= it).

        ``message`` is typed ``object`` (a supertype of the protocol's
        ``ProtocolTransportMessage``) so this module stays independent of the
        protocol type; at runtime it is always a :class:`ModelTransportMessage` this
        transport yielded from ``poll``, so it is narrowed here.
        """
        self._require_started()
        msg = cast(ModelTransportMessage, message)
        self._broker.commit_offset(msg.topic, self._group, msg.partition, msg.offset)
        if self._chaos_duplicate:
            token = (msg.topic, msg.partition, msg.offset)
            if token not in self._chaos_seen:
                self._chaos_seen.add(token)
                record = self._broker.record_at(msg.topic, msg.partition, msg.offset)
                if record is not None:
                    self._chaos_pending.append(record)

    async def nack(self, message: object) -> None:
        """Re-expose ``message`` and later same-partition offsets (mirrors seek).

        ``message`` is typed ``object`` for the same protocol-independence reason as
        :meth:`commit`; it is narrowed to the concrete transport message here.
        """
        self._require_started()
        msg = cast(ModelTransportMessage, message)
        cursor = (msg.topic, msg.partition)
        current = self._position(msg.topic, msg.partition)
        self._positions[cursor] = min(current, msg.offset)

    # -- producer protocol -------------------------------------------------

    async def send(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> None:
        """Append one event to the shared log, awaiting the (synchronous) ack."""
        self._broker.append(topic, key, value, headers)
