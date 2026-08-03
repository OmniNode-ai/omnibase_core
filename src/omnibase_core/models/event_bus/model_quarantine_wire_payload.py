# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Canonical pre-ack quarantine Kafka wire payload (OMN-15667).

Causal invariant: a Kafka record cannot contain the broker partition/offset
assigned by publishing that same record. ``ModelQuarantineWirePayload`` is the
PRE-ACK representation of a failed, unacknowledged primary-DLQ publish -- it
carries the authoritative source identity, a lossless copy of the original
record bytes, and typed evidence of why the primary-DLQ publish failed. It
has NO quarantine-topic/partition/offset fields, by construction: those
broker coordinates do not exist yet at the point this payload is built, and
``extra="forbid"`` rejects any attempt to smuggle them in.

Post-ack truth (the quarantine topic/partition/offset actually assigned by
the broker once THIS payload has been published to the quarantine topic)
lives exclusively in the separate ``ModelQuarantineDispositionReceipt``
(``omnibase_core.models.runtime``), constructed only after that publish is
acknowledged. The two models are never merged into one -- doing so would
require this payload to contain a value that cannot exist until after the
payload itself has already been serialized and accepted by the broker.

Frozen public Core name/field-set authority: Linear comment
cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb on OMN-15666 (2026-08-02T20:10:29Z),
which reaffirms the accepted OMN-15667 shape from the causal-audit comment
c54fcc0e-015c-431a-a095-68558eada2b5 (2026-08-02T18:41:06Z): "keeps every
existing top-level source field and primary_dlq_error_* field and adds exact
source_failure: ModelDeliveryFailureEvidence." Field set/names/types here are
pinned verbatim by the R2 harness reference
(tests/fixtures/omn_15663_r2/target_models.py in the READ-ONLY
omni_worktrees/OMN-15663/omninode_infra-renewal worktree) so Family A of
tests/gateway/test_omn_15663_r2_family_a_dlq_durability.py can turn green
later without any test edit.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_delivery_failure_evidence import (
    ModelDeliveryFailureEvidence,
)


class ModelQuarantineWirePayload(BaseModel):
    """Pre-ack quarantine Kafka wire payload for a failed primary-DLQ publish.

    Idempotency identity is exactly the four-field authoritative source
    tuple: ``(source_envelope_id, source_topic, source_partition,
    source_offset)``. Replaying the identical tuple must be recognized as the
    same logical quarantine event; a distinct ``source_offset`` is always a
    distinct event.
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
    primary_dlq_error_type: str = Field(
        ...,
        description="Exception/error class name observed publishing to the primary DLQ.",
    )
    primary_dlq_error_message: str = Field(
        ...,
        description="Error message observed publishing to the primary DLQ.",
    )
    source_failure: ModelDeliveryFailureEvidence = Field(
        ...,
        description="Typed evidence of the failed primary-DLQ publish attempt.",
    )


__all__ = ["ModelQuarantineWirePayload"]
