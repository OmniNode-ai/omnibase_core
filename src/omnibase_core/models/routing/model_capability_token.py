# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Capability token model for signed capability attestations.

A capability token is a signed assertion from a trusted issuer that a
specific node possesses certain capabilities. Tokens are verified at
resolution time to ensure that only nodes with valid attestations can
be resolved at tiers beyond ``local_exact``.

Tokens are immutable, self-contained, and carry the issuer's public key
and Ed25519 signature for independent verification.

.. versionadded:: 0.21.0
    Phase 3 of authenticated dependency resolution (OMN-2892).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCapabilityToken"]


class ModelCapabilityToken(BaseModel):
    """Signed capability attestation for a node.

    Attributes:
        token_id: Unique identifier for this token instance.
        subject_node_id: The node that this token attests capabilities for.
        issuer_domain: The trust domain that issued this token
            (e.g., ``org.omninode``, ``fed.partner-a``).
        capabilities: List of capability identifiers this token attests
            (e.g., ``["database.relational", "cache.redis"]``).
        issued_at: When the token was issued (UTC).
        expires_at: When the token expires (UTC). Resolution rejects
            expired tokens.
        issuer_public_key: Base64-encoded Ed25519 public key of the issuer.
            Used to verify the signature independently.
        signature: Base64-encoded Ed25519 signature over the token payload.
            The signed payload is the canonical JSON of all fields except
            ``signature`` itself.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    token_id: UUID = Field(
        ...,
        description="Unique identifier for this token instance",
    )

    subject_node_id: str = Field(
        ...,
        description="Node that this token attests capabilities for",
        min_length=1,
        max_length=256,
    )

    issuer_domain: str = Field(
        ...,
        description="Trust domain that issued this token",
        min_length=1,
        max_length=128,
    )

    capabilities: list[str] = Field(
        ...,
        description="Capability identifiers this token attests",
        min_length=1,
    )

    issued_at: datetime = Field(
        ...,
        description="When the token was issued (UTC)",
    )

    expires_at: datetime = Field(
        ...,
        description="When the token expires (UTC)",
    )

    issuer_public_key: str = Field(
        ...,
        description="Base64-encoded Ed25519 public key of the issuer",
        min_length=1,
    )

    signature: str = Field(
        ...,
        description="Base64-encoded Ed25519 signature over the token payload",
        min_length=1,
    )
