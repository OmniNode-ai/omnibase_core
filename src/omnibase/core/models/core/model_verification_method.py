"""
VerificationMethod model.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class ModelVerificationMethod(BaseModel):
    """Method used to establish trust."""

    method_name: str = Field(
        ..., description="Verification method name", pattern="^[a-z][a-z0-9_]*$"
    )

    verifier: str = Field(..., description="Entity that performed verification")

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When verification occurred",
    )

    signature: Optional[str] = Field(
        None, description="Cryptographic signature if applicable"
    )

    details: Optional[str] = Field(None, description="Additional verification details")


# Backward compatibility alias
VerificationMethod = ModelVerificationMethod
