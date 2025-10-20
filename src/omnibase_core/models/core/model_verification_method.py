from datetime import datetime

from pydantic import Field

"""
VerificationMethod model.
"""

from datetime import UTC

from pydantic import BaseModel


class ModelVerificationMethod(BaseModel):
    """Method used to establish trust."""

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
