"""Encryption Metadata Model.

Metadata for encrypted envelope payloads.
"""

from typing import Any

from pydantic import BaseModel, Field


class ModelEncryptionMetadata(BaseModel):
    """Metadata for encrypted envelope payloads."""

    algorithm: str = Field(..., description="Encryption algorithm (AES-256-GCM, etc.)")
    key_id: str = Field(..., description="Encryption key identifier")
    iv: str = Field(..., description="Base64-encoded initialization vector")
    auth_tag: str = Field(..., description="Base64-encoded authentication tag")
    encrypted_key: str | None = Field(
        None,
        description="Encrypted symmetric key (for asymmetric)",
    )
    recipient_keys: dict[str, str] = Field(
        default_factory=dict,
        description="Per-recipient encrypted keys",
    )
