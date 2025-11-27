"""Encryption Metadata Model.

Metadata for encrypted envelope payloads.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelEncryptionMetadata(BaseModel):
    """Metadata for encrypted envelope payloads."""

    algorithm: str = Field(
        default=..., description="Encryption algorithm (AES-256-GCM, etc.)"
    )
    key_id: UUID = Field(default=..., description="Encryption key identifier")
    iv: str = Field(default=..., description="Base64-encoded initialization vector")
    auth_tag: str = Field(default=..., description="Base64-encoded authentication tag")
    encrypted_key: str | None = Field(
        default=None,
        description="Encrypted symmetric key (for asymmetric)",
    )
    recipient_keys: dict[str, str] = Field(
        default_factory=dict,
        description="Per-recipient encrypted keys",
    )
