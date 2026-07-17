# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Pull-based transport consumer protocol.

Net-new, currently UNUSED (ticket OMN-14719, epic OMN-14717; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` section
(c)). The unified runtime depends only on this abstraction; concrete transports
(Kafka in infra, in-memory in core) implement it and point inward via DI, so core
never imports Kafka.

Design notes (authoritative in plan section (c)/(d)):

* Deliberately **pull-based** (``poll``), NOT push (``subscribe(on_message=...)``).
  Pull is the load-bearing inversion: it lets the runtime own commit timing.
* Assigned topics + consumer group are construction-time config supplied by the
  composition root, not a runtime-called method — this removes the "who commits"
  ambiguity of the push callback surface.
* ``commit`` advances the per-partition high-water mark: committing a message's
  offset implicitly commits every earlier offset on that partition.
* ``nack`` does NOT advance the cursor — it makes that message and all later
  same-partition offsets redeliverable (Kafka: ``seek``).
* There is **no** ``dlq()`` method. DLQ is runtime policy expressed with the two
  primitives the protocols already have (``producer.send(dlq_topic, ...)`` then
  ``consumer.commit(original)``), so DLQ is defined once, in the runtime.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from omnibase_core.protocols.runtime.protocol_transport_message import (
    ProtocolTransportMessage,
)


@runtime_checkable
class ProtocolTransportConsumer(Protocol):
    """Runtime-owned, pull-based consumer over a single transport."""

    async def start(self) -> None:
        """Establish the underlying consumer / connection."""
        raise NotImplementedError  # stub-ok: protocol method body

    async def close(self) -> None:
        """Tear down the underlying consumer / connection."""
        raise NotImplementedError  # stub-ok: protocol method body

    async def poll(
        self, *, max_messages: int, timeout_ms: int
    ) -> Sequence[ProtocolTransportMessage]:
        """Pull up to ``max_messages`` messages, waiting at most ``timeout_ms``.

        ``max_messages`` bounds the in-flight batch (backpressure). Messages from a
        single partition are returned in ascending ``offset`` order.
        """
        raise NotImplementedError  # stub-ok: protocol method body

    async def commit(self, message: ProtocolTransportMessage) -> None:
        """Advance the partition high-water mark to ``message`` (commits all <= it)."""
        raise NotImplementedError  # stub-ok: protocol method body

    async def nack(self, message: ProtocolTransportMessage) -> None:
        """Hold: make ``message`` and later same-partition offsets redeliverable."""
        raise NotImplementedError  # stub-ok: protocol method body


__all__ = ["ProtocolTransportConsumer"]
