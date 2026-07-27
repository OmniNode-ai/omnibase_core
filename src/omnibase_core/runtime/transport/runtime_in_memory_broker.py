# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Shared in-memory broker backing the in-memory transport.

Net-new foundation for the single-runtime / transport-via-DI unification (epic
OMN-14717, ticket OMN-14720; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` sections
(c)/(d.4)). Nothing in production wires it yet — reversible, zero behavior change.

The broker is the append-only log + per-``(topic, group, partition)`` committed
cursor that every in-memory producer/consumer sharing it sees. Records are
append-only (never removed); a consumer group's *durability* is the committed
offset; a consumer instance's *fetch position* is instance-local (owned by
``InMemoryTransport``) so a restart resumes from the committed offset. This is what
makes the in-memory transport model Kafka's monotonic per-partition offset (plan
HOLE 2), not SQS per-message ack.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.runtime.model_transport_message import ModelTransportMessage

__all__ = ["InMemoryBroker"]


class InMemoryBroker:
    """Append-only log + per-group committed cursor shared by in-memory transports.

    ``num_partitions`` controls partition fan-out. Partition assignment is
    deterministic: keyed messages hash to a stable partition; unkeyed messages
    round-robin per topic in send order. The stored value is a canonical
    :class:`ModelTransportMessage` whose opaque ``ack_token`` is the
    ``(topic, partition, offset)`` coordinate (group-independent — the runtime never
    interprets it).
    """

    def __init__(self, num_partitions: int = 1) -> None:
        if num_partitions < 1:
            raise ModelOnexError(
                f"num_partitions must be a positive integer, got {num_partitions}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
        self.num_partitions = num_partitions
        # topic -> partition index -> append-ordered messages (offset == list index).
        self._logs: dict[str, list[list[ModelTransportMessage]]] = {}
        # (topic, group, partition) -> highest committed offset (-1 == none committed).
        self._committed: dict[tuple[str, str, int], int] = {}
        # topic -> monotonic counter for round-robin assignment of unkeyed messages.
        self._round_robin: dict[str, int] = {}

    def _select_partition(self, topic: str, key: bytes | None) -> int:
        if self.num_partitions == 1:
            return 0
        if key is None:
            counter = self._round_robin.get(topic, 0)
            self._round_robin[topic] = counter + 1
            return counter % self.num_partitions
        digest = hashlib.sha256(key).digest()
        return int.from_bytes(digest[:8], "big") % self.num_partitions

    def append(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> ModelTransportMessage:
        """Append one message, assigning partition + offset deterministically."""
        partition = self._select_partition(topic, key)
        partitions = self._logs.setdefault(
            topic, [[] for _ in range(self.num_partitions)]
        )
        log = partitions[partition]
        offset = len(log)
        message = ModelTransportMessage(
            topic=topic,
            partition=partition,
            offset=offset,
            key=key,
            value=value,
            headers=dict(headers),
            ack_token=(topic, partition, offset),
        )
        log.append(message)
        return message

    def records(self, topic: str, partition: int) -> Sequence[ModelTransportMessage]:
        partitions = self._logs.get(topic)
        if partitions is None:
            return ()
        return partitions[partition]

    def record_at(
        self, topic: str, partition: int, offset: int
    ) -> ModelTransportMessage | None:
        log = self.records(topic, partition)
        if 0 <= offset < len(log):
            return log[offset]
        return None

    def committed_offset(self, topic: str, group: str, partition: int) -> int:
        return self._committed.get((topic, group, partition), -1)

    def commit_offset(
        self, topic: str, group: str, partition: int, offset: int
    ) -> None:
        """Advance the committed high-water mark to ``offset`` (commits all <= it).

        The high-water mark is monotonic: committing an offset at or below the
        current mark is a no-op. Committing offset ``k`` records that every offset
        ``<= k`` on this partition is durable — a later consumer instance on the same
        group will not be redelivered any of them.
        """
        key = (topic, group, partition)
        if offset > self._committed.get(key, -1):
            self._committed[key] = offset
