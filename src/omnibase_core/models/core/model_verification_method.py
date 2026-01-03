"""
VerificationMethod model.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelVerificationMethod(BaseModel):
    """Immutable verification method used to establish trust."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    method_name: str = Field(
        default=...,
        description="Verification method name",
        pattern="^[a-z][a-z0-9_]*$",
    )

    verifier: str = Field(default=..., description="Entity that performed verification")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When verification occurred",
    )

    signature: str | None = Field(
        default=None,
        description="Cryptographic signature if applicable",
    )

    details: str | None = Field(
        default=None, description="Additional verification details"
    )


# Compatibility alias
VerificationMethod = ModelVerificationMethod
