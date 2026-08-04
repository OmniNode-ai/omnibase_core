# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Broker publish acknowledgement (OMN-15666).

The ONLY admissible proof that a publish became durable. Every dual-sink
branch in :mod:`omnibase_core.runtime.runtime_dual_sink` is gated on receiving
one of these: an enqueue intent, a successful serialization, a swallowed
exception, or an un-awaited publish future is NEVER a durability signal.

``topic``/``partition``/``offset`` are copied verbatim from the broker's own
acknowledgement — never the caller's *intended* topic and never a sentinel. A
negative coordinate is rejected outright: ``-1`` is the canonical "the broker
did not tell us" value, and accepting it would let a fabricated coordinate
masquerade as durable evidence.

Frozen public Core name/field-set authority: Linear comment
``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666 (2026-08-02T20:10:29Z) --
"``ModelTransportPublishAcknowledgement``: strict/frozen topic, nonnegative
partition, nonnegative offset copied from the broker acknowledgement."
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelTransportPublishAcknowledgement(BaseModel):
    """Strict, frozen record of one broker-acknowledged publish."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    topic: str = Field(
        ...,
        description="Topic the broker acknowledged the publish on.",
    )
    partition: int = Field(
        ...,
        description="Partition assigned by the broker acknowledgement.",
        ge=0,
    )
    offset: int = Field(
        ...,
        description="Offset assigned by the broker acknowledgement.",
        ge=0,
    )


__all__ = ["ModelTransportPublishAcknowledgement"]
