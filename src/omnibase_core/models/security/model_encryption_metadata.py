"""Encryption Metadata Model.

Metadata for encrypted envelope payloads including cryptographic parameters,
key identifiers, and integrity verification data.

This module provides the ModelEncryptionMetadata class used to store all
cryptographic metadata required to decrypt an encrypted payload in a
ModelSecureEventEnvelope.

Example:
    >>> from uuid import uuid4
    >>> metadata = ModelEncryptionMetadata(
    ...     algorithm="AES-256-GCM",
    ...     key_id=uuid4(),
    ...     iv="base64_encoded_iv==",
    ...     auth_tag="base64_encoded_tag==",
    ... )
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelEncryptionMetadata(BaseModel):
    """Metadata for encrypted envelope payloads.

    Stores all cryptographic parameters required for decryption of encrypted
    payloads in ModelSecureEventEnvelope. This includes the algorithm used,
    key identifiers, initialization vector, authentication tag, and optional
    fields for asymmetric encryption scenarios.

    The model supports both symmetric encryption (single key) and asymmetric
    encryption with multiple recipients (per-recipient encrypted keys).

    Attributes:
        algorithm: The encryption algorithm used (e.g., "AES-256-GCM").
            Currently only AES-256-GCM is supported for encryption.
        key_id: Unique identifier for the encryption key. For PBKDF2-derived
            keys, this UUID's bytes are used as the salt.
        iv: Base64-encoded initialization vector (nonce). For AES-GCM,
            this is typically 12 bytes (96 bits).
        auth_tag: Base64-encoded authentication tag from AES-GCM. This
            16-byte tag ensures ciphertext integrity and authenticity.
        aad_hash: SHA-256 hash of the Additional Authenticated Data (AAD)
            used during encryption. AAD binds the ciphertext to envelope
            metadata to prevent ciphertext transplantation attacks.
        encrypted_key: Base64-encoded encrypted symmetric key for asymmetric
            encryption scenarios where the data key is encrypted with a
            public key.
        recipient_keys: Mapping of recipient identifiers to their individually
            encrypted copies of the symmetric key, enabling multi-recipient
            encryption.

    Example:
        >>> from uuid import uuid4
        >>> # Create metadata for AES-256-GCM encryption
        >>> metadata = ModelEncryptionMetadata(
        ...     algorithm="AES-256-GCM",
        ...     key_id=uuid4(),
        ...     iv="SGVsbG9Xb3JsZA==",
        ...     auth_tag="dGVzdF9hdXRoX3RhZw==",
        ...     aad_hash="abc123...",
        ... )
        >>> metadata.algorithm
        'AES-256-GCM'

    Note:
        This model uses from_attributes=True to support pytest-xdist parallel
        execution where class identity may differ between workers.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    algorithm: str = Field(
        default=..., description="Encryption algorithm (AES-256-GCM, etc.)"
    )
    key_id: UUID = Field(default=..., description="Encryption key identifier")
    iv: str = Field(default=..., description="Base64-encoded initialization vector")
    auth_tag: str = Field(default=..., description="Base64-encoded authentication tag")
    aad_hash: str | None = Field(
        default=None,
        description="SHA-256 hash of Additional Authenticated Data (AAD) used in encryption. "
        "AAD binds ciphertext to envelope metadata (envelope_id, source_node_id, timestamp) "
        "to prevent ciphertext transplantation attacks.",
    )
    encrypted_key: str | None = Field(
        default=None,
        description="Encrypted symmetric key (for asymmetric)",
    )
    recipient_keys: dict[str, str] = Field(
        default_factory=dict,
        description="Per-recipient encrypted keys",
    )
