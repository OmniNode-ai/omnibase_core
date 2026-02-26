# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolution proof model for verification audit trail.

A resolution proof records the outcome of verifying a specific proof
requirement during tiered resolution. Each proof links to the proof type,
the verification result, and optionally the capability token that was
verified.

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_proof_type import EnumProofType
from omnibase_core.models.routing.model_capability_token import ModelCapabilityToken

__all__ = ["ModelResolutionProof"]


class ModelResolutionProof(BaseModel):
    """Record of a proof verification during tiered resolution.

    Attributes:
        proof_type: The type of proof that was verified.
        verified: Whether the proof passed verification.
        verification_notes: Human-readable notes about the verification
            outcome (e.g., reason for failure, verification method used).
        token: The capability token that was verified, if applicable.
            Only present for ``capability_attested`` proof types.
        verified_at: When the verification was performed (UTC).
            None if verification was not attempted.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    proof_type: EnumProofType = Field(
        ...,
        description="Type of proof that was verified",
    )

    verified: bool = Field(
        ...,
        description="Whether the proof passed verification",
    )

    verification_notes: str = Field(
        ...,
        description="Human-readable notes about verification outcome",
    )

    token: ModelCapabilityToken | None = Field(
        default=None,
        description="Capability token that was verified, if applicable",
    )

    verified_at: datetime | None = Field(
        default=None,
        description="When verification was performed (UTC)",
    )
