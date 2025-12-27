"""
ModelEncryptionAlgorithm: Encryption algorithm configuration.

This model represents encryption algorithm specifications and parameters.
"""

from pydantic import BaseModel, Field, field_validator


class ModelEncryptionAlgorithm(BaseModel):
    """Encryption algorithm configuration and parameters."""

    name: str = Field(
        default=...,
        description="Algorithm name: AES-256-GCM, AES-256-CBC, ChaCha20-Poly1305, etc.",
        pattern=r"^[A-Z0-9-]+$",
    )

    key_size_bits: int = Field(
        default=256, description="Key size in bits", ge=128, le=512
    )

    block_size_bits: int | None = Field(
        default=128,
        description="Block size in bits for block ciphers",
        ge=64,
        le=256,
    )

    mode: str | None = Field(
        default=None,
        description="Cipher mode: GCM, CBC, CTR, etc.",
        pattern=r"^[A-Z]+$",
    )

    is_authenticated: bool = Field(
        default=True,
        description="Whether this is an authenticated encryption algorithm (AEAD)",
    )

    tag_size_bits: int | None = Field(
        default=128,
        description="Authentication tag size in bits for AEAD algorithms",
        ge=64,
        le=256,
    )

    iv_size_bits: int = Field(
        default=96,
        description="Initialization vector size in bits",
        ge=64,
        le=256,
    )

    is_stream_cipher: bool = Field(
        default=False, description="Whether this is a stream cipher"
    )

    security_level: str = Field(
        default="high",
        description="Security level: low, medium, high, military",
        pattern=r"^(low|medium|high|military)$",
    )

    performance_rating: str = Field(
        default="medium",
        description="Performance rating: slow, medium, fast",
        pattern=r"^(slow|medium|fast)$",
    )

    @field_validator("name")
    @classmethod
    def validate_algorithm_name(cls, v: str) -> str:
        """Validate algorithm name against known algorithms."""
        known_algorithms = {
            "AES-256-GCM",
            "AES-256-CBC",
            "AES-128-GCM",
            "AES-128-CBC",
            "ChaCha20-Poly1305",
            "XChaCha20-Poly1305",
            "3DES-CBC",
            "Blowfish-CBC",
            "Twofish-CBC",
        }
        if v not in known_algorithms:
            from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
            from omnibase_core.errors import ModelOnexError

            raise ModelOnexError(
                message=f"Unsupported encryption algorithm: {v}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                context={
                    "algorithm": v,
                    "supported_algorithms": sorted(known_algorithms),
                },
            )

        return v

    def is_compatible_with(self, other: "ModelEncryptionAlgorithm") -> bool:
        """Check if this algorithm is compatible with another."""
        # Same algorithm family
        if self.name.split("-")[0] == other.name.split("-")[0]:
            return True
        # Both are AEAD
        return bool(self.is_authenticated and other.is_authenticated)

    @classmethod
    def create_aes_256_gcm(cls) -> "ModelEncryptionAlgorithm":
        """Create AES-256-GCM algorithm configuration."""
        return cls(
            name="AES-256-GCM",
            key_size_bits=256,
            block_size_bits=128,
            mode="GCM",
            is_authenticated=True,
            tag_size_bits=128,
            iv_size_bits=96,
            is_stream_cipher=False,
            security_level="high",
            performance_rating="fast",
        )

    @classmethod
    def create_chacha20_poly1305(cls) -> "ModelEncryptionAlgorithm":
        """Create ChaCha20-Poly1305 algorithm configuration."""
        return cls(
            name="ChaCha20-Poly1305",
            key_size_bits=256,
            block_size_bits=None,
            mode=None,
            is_authenticated=True,
            tag_size_bits=128,
            iv_size_bits=96,
            is_stream_cipher=True,
            security_level="high",
            performance_rating="fast",
        )
