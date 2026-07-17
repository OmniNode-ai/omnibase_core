# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Transport producer protocol.

Net-new, currently UNUSED (ticket OMN-14719, epic OMN-14717; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` section
(c)). The unified runtime depends only on this abstraction; concrete transports
implement it and point inward via DI, so core never imports Kafka.

``send`` awaits the broker acknowledgement for a single event. DLQ is not a producer
concern — the runtime expresses DLQ as ``send(dlq_topic, ...)`` followed by
``consumer.commit(original)``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProtocolTransportProducer(Protocol):
    """Runtime-owned producer over a single transport."""

    async def send(
        self,
        topic: str,
        key: bytes | None,
        value: bytes,
        headers: Mapping[str, bytes],
    ) -> None:
        """Publish one event to ``topic`` and await the broker acknowledgement."""
        ...


__all__ = ["ProtocolTransportProducer"]
