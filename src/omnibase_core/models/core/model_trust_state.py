"""
Trust State Model.

Extensible trust state model that replaces string literals with
rich metadata for trust verification and management.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from .model_verification_method import ModelVerificationMethod


class ModelTrustState(BaseModel):
    """
    Extensible trust state model.

    Replaces string literals with rich trust metadata that can be
    extended by plugins and third-party systems.
    """

    trust_level: str = Field(
        default=...,
        description="Trust level identifier",
        pattern="^[a-z][a-z0-9_]*$",
    )
    trust_score: float = Field(
        default=..., description="Numeric trust score", ge=0.0, le=1.0
    )
    verification_methods: list[ModelVerificationMethod] = Field(
        default_factory=list,
        description="Methods used to verify trust",
    )
    last_verified: datetime | None = Field(
        default=None,
        description="Last verification timestamp",
    )
    expires_at: datetime | None = Field(default=None, description="When trust expires")
    issuer: str | None = Field(default=None, description="Trust issuer identifier")
    revocable: bool = Field(default=True, description="Whether trust can be revoked")

    def is_trusted(self, threshold: float = 0.5) -> bool:
        """Check if trust score meets threshold."""
        return self.trust_score >= threshold

    def is_expired(self) -> bool:
        """Check if trust has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


# Compatibility alias
TrustState = ModelTrustState
