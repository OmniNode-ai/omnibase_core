"""
ModelEncryptionRequirement: Encryption requirement configuration.

This model defines encryption requirements and settings for payloads.
"""

from pydantic import BaseModel, Field, field_validator

from .model_encryption_algorithm import ModelEncryptionAlgorithm


class ModelEncryptionRequirement(BaseModel):
    """Encryption requirement configuration for payloads."""

    level: str = Field(
        "optional",
        description="Requirement level: none, optional, required, always",
        pattern=r"^(none|optional|required|always)$",
    )

    minimum_key_size: int = Field(
        256,
        description="Minimum encryption key size in bits",
        ge=128,
    )

    allowed_algorithms: list[ModelEncryptionAlgorithm] = Field(
        default_factory=lambda: [
            ModelEncryptionAlgorithm.create_aes_256_gcm(),
            ModelEncryptionAlgorithm(
                name="AES-256-CBC",
                key_size_bits=256,
                mode="CBC",
                is_authenticated=False,
            ),
            ModelEncryptionAlgorithm.create_chacha20_poly1305(),
        ],
        description="Allowed encryption algorithms",
    )

    require_authenticated_encryption: bool = Field(
        True,
        description="Require authenticated encryption modes (AEAD)",
    )

    key_rotation_days: int = Field(
        90,
        description="Maximum key age before rotation required",
        ge=1,
    )

    encrypt_metadata: bool = Field(
        False,
        description="Whether to also encrypt envelope metadata",
    )

    compression_before_encryption: bool = Field(
        True,
        description="Whether to compress data before encryption",
    )

    fallback_algorithm: ModelEncryptionAlgorithm | None = Field(
        default_factory=lambda: ModelEncryptionAlgorithm(
            name="AES-256-CBC",
            key_size_bits=256,
            mode="CBC",
            is_authenticated=False,
            security_level="medium",
        ),
        description="Fallback algorithm if primary not available",
    )

    exemption_roles: list[str] = Field(
        default_factory=list,
        description="Roles that can bypass encryption requirements",
    )

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate encryption requirement level."""
        valid_levels = {"none", "optional", "required", "always"}
        if v not in valid_levels:
            msg = f"Invalid encryption level: {v}. Must be one of: {valid_levels}"
            raise ValueError(
                msg,
            )
        return v

    def is_encryption_required(self, has_sensitive_data: bool = False) -> bool:
        """Check if encryption is required based on level and data sensitivity."""
        if self.level == "always" or (self.level == "required" and has_sensitive_data):
            return True
        if self.level == "optional":
            return False
        # none
        return False

    def get_preferred_algorithm(self) -> ModelEncryptionAlgorithm:
        """Get the preferred encryption algorithm."""
        if self.allowed_algorithms:
            return self.allowed_algorithms[0]
        return self.fallback_algorithm or ModelEncryptionAlgorithm.create_aes_256_gcm()
