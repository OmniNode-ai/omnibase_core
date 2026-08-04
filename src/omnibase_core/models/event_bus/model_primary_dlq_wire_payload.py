# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical pre-ack primary-DLQ Kafka wire payload (OMN-15666).

The primary-sink twin of OMN-15667's ``ModelQuarantineWirePayload``, and it
obeys the same causal invariant: a Kafka record cannot contain the broker
partition/offset assigned by publishing that same record, so this payload has
NO ``primary_dlq_topic``/``primary_dlq_partition``/``primary_dlq_offset``
fields by construction and ``extra="forbid"`` rejects any attempt to smuggle
them in. Post-ack truth lives exclusively in the separate
``ModelPrimaryDlqDispositionReceipt`` (``omnibase_core.models.runtime``).

The difference from the quarantine payload is causal, not cosmetic: this one
describes a source record whose HANDLING failed (``source_failure`` names the
handler/coercion/routing stage that exhausted), whereas the quarantine payload
additionally carries ``primary_dlq_error_*`` because by the time it is built,
the primary-DLQ publish itself has also failed.

Frozen public Core name/field-set authority: Linear comment
``cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb`` on OMN-15666 (2026-08-02T20:10:29Z) --
"``ModelPrimaryDlqWirePayload``: exact authoritative ``source_envelope_id:
UUID``, ``source_topic: str``, ``source_partition: int``, ``source_offset:
int``, canonical-base64 source key/value, ordered duplicate-preserving base64
header pairs, and ``source_failure: ModelDeliveryFailureEvidence``."
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)


class ModelPrimaryDlqWirePayload(BaseModel):
    """Pre-ack primary-DLQ Kafka wire payload for a source record that exhausted.

    Idempotency identity is exactly the four-field authoritative source tuple:
    ``(source_envelope_id, source_topic, source_partition, source_offset)`` --
    the same tuple ``ModelQuarantineWirePayload`` keys on, so a fallback does
    not change the logical event's identity.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_envelope_id: UUID = Field(
        ...,
        description="Envelope identifier of the original source record.",
    )
    source_topic: str = Field(
        ...,
        description="Topic the original source record was consumed from.",
    )
    source_partition: int = Field(
        ...,
        description="Partition the original source record was consumed from.",
        ge=0,
    )
    source_offset: int = Field(
        ...,
        description="Offset of the original source record within its partition.",
        ge=0,
    )
    source_key_b64: str = Field(
        ...,
        description="Standard-base64 encoding of the original record key bytes.",
    )
    source_value_b64: str = Field(
        ...,
        description="Standard-base64 encoding of the original record value bytes.",
    )
    source_headers_b64: tuple[tuple[str, str], ...] = Field(
        ...,
        description=(
            "Ordered, duplicate-preserving sequence of (header name, "
            "standard-base64 header value) pairs from the original record. "
            "Never a mapping: a mapping would silently collapse repeated "
            "header names and could reorder them."
        ),
    )
    source_failure: ModelDeliveryFailureEvidence = Field(
        ...,
        description=(
            "Typed evidence of the handling failure that exhausted this record's "
            "retry budget and sent it to the primary DLQ."
        ),
    )


__all__ = ["ModelPrimaryDlqWirePayload"]
