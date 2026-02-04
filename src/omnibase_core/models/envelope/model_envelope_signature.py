"""
Envelope signature model for cryptographic verification.

The signature binds the envelope's routing metadata and payload hash
to the runtime_id (gateway), establishing trust in the message origin.

Signature covers:
    - realm
    - runtime_id
    - bus_id
    - trace_id
    - emitted_at
    - payload_hash (Blake3 of payload)

The signature does NOT cover emitter_identity because:
    - emitter_identity is for observability, not authentication
    - The gateway (runtime_id) vouches for the message, not the component
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelEnvelopeSignature(BaseModel):
    """
    Cryptographic signature for envelope verification.

    The signature is created by the runtime gateway and verifies
    that the envelope contents have not been tampered with.

    Attributes:
        algorithm: Signing algorithm (always "ed25519").
        signer: Runtime ID that created the signature.
        payload_hash: Blake3 hash of the serialized payload.
        signature: Base64-encoded Ed25519 signature.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    algorithm: Literal["ed25519"] = Field(
        default="ed25519",
        description="Signing algorithm. Currently only ed25519 is supported.",
    )

    signer: str = Field(
        ...,
        min_length=1,
        description="Runtime ID that created this signature.",
    )

    payload_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="Blake3 hash of the payload (64 hex characters).",
    )

    signature: str = Field(
        ...,
        min_length=1,
        description="Base64-encoded Ed25519 signature.",
    )

    @field_validator("payload_hash")
    @classmethod
    def validate_payload_hash_hex(cls, v: str) -> str:
        """Validate that payload_hash contains only hex characters."""
        if not re.fullmatch(r"[0-9a-f]{64}", v, re.IGNORECASE):
            raise ValueError(
                "payload_hash must be exactly 64 hex characters (0-9, a-f)"
            )
        return v.lower()  # Normalize to lowercase


__all__ = ["ModelEnvelopeSignature"]
