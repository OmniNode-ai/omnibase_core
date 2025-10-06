"""Signature Verification Result Model.

Result of signature verification including chain validation and policy compliance.
"""

from pydantic import BaseModel, Field

from .model_chain_validation import ModelChainValidation
from .model_policy_validation import ModelPolicyValidation


class ModelSignatureVerificationResult(BaseModel):
    """Result of signature verification."""

    status: str = Field(..., description="Verification status")
    verified: bool = Field(..., description="Whether signatures are verified")
    signature_count: int = Field(..., description="Total signatures")
    verified_signatures: int = Field(..., description="Number of verified signatures")
    chain_validation: ModelChainValidation = Field(
        ...,
        description="Chain validation details",
    )
    policy_validation: ModelPolicyValidation | None = Field(
        default=None,
        description="Policy validation if applicable",
    )
    verified_at: str = Field(..., description="Verification timestamp")
