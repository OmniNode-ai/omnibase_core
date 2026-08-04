# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The dual-sink terminal disposition INPUT (OMN-15666).

One immutable record describing "this source record exhausted; terminalize it".
It is the join of the two merged parent seams:

* the four ``source_*`` fields ARE the OMN-15665 ``ModelDeliveryContext``
  (``envelope_id``/``topic``/``partition``/``offset``) — copied verbatim by
  ``build_terminal_disposition_request``, never a ``correlation_id`` alias and
  never a fresh ``uuid4()`` (OMN-15666 acceptance criterion 1);
* the base64 source bytes + ordered duplicate-preserving headers + typed
  ``source_failure`` are exactly the fields OMN-15667's
  ``ModelQuarantineWirePayload`` requires, so the fallback payload is a
  projection of this request rather than a re-derivation.

It additionally carries the two INTENDED sink topics. They are intents, not
evidence: neither ever appears in a receipt. A receipt's topic is always the
one the broker acknowledged.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)


class ModelTerminalDispositionRequest(BaseModel):
    """Immutable input to the dual-sink terminal disposition."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source_envelope_id: UUID = Field(
        ...,
        description=(
            "Authoritative envelope id of the source record, taken verbatim from "
            "its ModelDeliveryContext — never a correlation_id, never uuid4()."
        ),
    )
    source_topic: str = Field(
        ...,
        description="Topic the source record was consumed from.",
    )
    source_partition: int = Field(
        ...,
        description="Partition the source record was consumed from.",
        ge=0,
    )
    source_offset: int = Field(
        ...,
        description="Offset of the source record within its partition.",
        ge=0,
    )
    primary_dlq_topic: str = Field(
        ...,
        description=(
            "INTENDED primary DLQ topic. An intent, never durability evidence — "
            "the receipt records the topic the broker acknowledged."
        ),
    )
    quarantine_topic: str = Field(
        ...,
        description=(
            "INTENDED canonical quarantine topic, attempted only after the "
            "primary DLQ publish fails."
        ),
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
            "Ordered, duplicate-preserving (header name, base64 header value) "
            "pairs from the original record. Never a mapping."
        ),
    )
    source_failure: ModelDeliveryFailureEvidence = Field(
        ...,
        description=(
            "Typed evidence of the handling failure that exhausted this record's "
            "retry budget."
        ),
    )


__all__ = ["ModelTerminalDispositionRequest"]
