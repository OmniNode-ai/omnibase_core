# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical post-ack primary-DLQ disposition receipt (OMN-15666).

``ModelPrimaryDlqDispositionReceipt`` is the sole surface carrying primary-DLQ
broker coordinates (``primary_dlq_topic``/``primary_dlq_partition``/
``primary_dlq_offset``). It exists only AFTER the broker has acknowledged the
publish of a ``ModelPrimaryDlqWirePayload`` to the primary DLQ topic; it is
never serialized as that same Kafka record. Exactly the causal split OMN-15667
landed for the quarantine sink (``ModelQuarantineDispositionReceipt``), applied
to the primary sink.

Its existence is the ONLY thing that licenses committing the source offset on
the primary-ack branch. Constructing one from an intent, a serialization, or an
un-awaited future is a contract violation, not a shortcut.

Frozen public Core name/field-set authority: Linear comment
``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666 (2026-08-02T20:10:29Z) --
"``ModelPrimaryDlqDispositionReceipt``: exact ``primary_dlq_payload`` plus
broker-returned ``primary_dlq_topic``, ``primary_dlq_partition``, and
``primary_dlq_offset``."
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_primary_dlq_wire_payload import (
    ModelPrimaryDlqWirePayload,
)


class ModelPrimaryDlqDispositionReceipt(BaseModel):
    """Post-ack primary-DLQ disposition receipt.

    Carries the exact validated pre-ack wire payload plus the broker
    acknowledgement's primary-DLQ topic/partition/offset. Constructed only
    after that acknowledgement is observed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary_dlq_payload: ModelPrimaryDlqWirePayload = Field(
        ...,
        description=(
            "The exact validated pre-ack primary-DLQ wire payload that was published."
        ),
    )
    primary_dlq_topic: str = Field(
        ...,
        description="Primary DLQ topic the payload was published to.",
    )
    primary_dlq_partition: int = Field(
        ...,
        description="Partition assigned by the broker acknowledgement.",
        ge=0,
    )
    primary_dlq_offset: int = Field(
        ...,
        description="Offset assigned by the broker acknowledgement.",
        ge=0,
    )


__all__ = ["ModelPrimaryDlqDispositionReceipt"]
