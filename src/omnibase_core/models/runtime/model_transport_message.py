# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical transport-message model for the unified runtime dispatch loop.

Net-new, currently UNUSED foundation for the single-runtime / transport-via-DI
unification (epic OMN-14717, ticket OMN-14719; see
``docs/plans/2026-07-17-single-runtime-transport-di-unification-plan.md`` section
(c)). Nothing consumes this yet — it is reversible foundation with zero production
behavior change.

``ModelTransportMessage`` is the transport-agnostic wire message that the pull-based
``ProtocolTransportConsumer`` yields and that the runtime commits / nacks. It carries
per-partition identity (``partition`` + ``offset``) because the runtime's
per-partition contiguous-prefix commit (plan HOLE 1) and the in-memory transport's
monotonic per-``(topic, group, partition)`` offset cursor (plan HOLE 2) both need to
group a poll batch by partition and order by offset. The commit/redeliver *actuation*
coordinate stays opaque in ``ack_token`` — the runtime never interprets it, which is
what makes the Kafka and in-memory transports substitutable.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field


class ModelTransportMessage(BaseModel):
    """One message pulled from a transport, independent of the concrete broker.

    Frozen value object. ``partition`` and ``offset`` are REQUIRED: they are the
    per-partition identity and the monotonic cursor coordinate the runtime and the
    in-memory transport both depend on. ``ack_token`` is opaque — the runtime hands
    it straight back to ``commit()`` / ``nack()`` and never inspects it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(..., description="Source topic the message was polled from.")
    partition: int = Field(
        ...,
        description="Partition the message belongs to (per-partition identity).",
    )
    offset: int = Field(
        ...,
        description="Monotonic per-partition offset coordinate of the message.",
    )
    key: bytes | None = Field(
        ...,
        description="Raw partition / routing key, or None when the message is unkeyed.",
    )
    value: bytes = Field(..., description="Raw message payload bytes.")
    headers: Mapping[str, bytes] = Field(
        ...,
        description="Raw transport headers (header name -> raw bytes).",
    )
    ack_token: object = Field(
        ...,
        description=(
            "Opaque cursor the transport uses to commit / redeliver this message. "
            "The runtime NEVER interprets it — it hands it back to commit() / nack(). "
            "For Kafka it wraps the TopicPartition+offset; for the in-memory transport "
            "the queue coordinate."
        ),
    )


__all__ = ["ModelTransportMessage"]
