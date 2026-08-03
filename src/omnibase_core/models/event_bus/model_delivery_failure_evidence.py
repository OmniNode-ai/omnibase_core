# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed delivery-failure evidence for a failed transport publish.

Canonical shared evidence type embedded in the pre-ack quarantine wire
payload (``ModelQuarantineWirePayload``, OMN-15667) as ``source_failure``.
Frozen public Core name/field-set authority: Linear comment
cfb64e0f-c2e6-4ae2-94cf-308c7e1a1efb on OMN-15666 (2026-08-02T20:10:29Z).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelDeliveryFailureEvidence(BaseModel):
    """Typed evidence describing why a transport publish attempt failed.

    Replaces a bare ``str`` error message with a strict, structured record so
    a quarantine consumer can classify the failure (stage, error type,
    retryability) without parsing free text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    stage: str = Field(
        ...,
        description=(
            "Delivery stage that failed, e.g. 'primary_dlq_publish' or "
            "'quarantine_publish'."
        ),
    )
    error_type: str = Field(
        ...,
        description="Exception/error class name observed at the failing stage.",
    )
    error_message: str = Field(
        ...,
        description="Human-readable error message observed at the failing stage.",
    )
    retryable: bool = Field(
        ...,
        description="Whether the observed failure is considered retryable.",
    )


__all__ = ["ModelDeliveryFailureEvidence"]
