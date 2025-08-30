"""
ModelSignatureVerificationResult: Result of signature verification.

This model represents the comprehensive result of cryptographic signature
verification including chain validation and policy compliance.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelChainValidation(BaseModel):
    """Chain validation details."""

    chain_id: str = Field(..., description="Chain identifier")
    envelope_id: str = Field(..., description="Envelope identifier")
    signature_count: int = Field(..., description="Total signatures in chain")
    unique_signers: int = Field(..., description="Number of unique signers")
    operations: List[str] = Field(..., description="Operations performed")
    algorithms: List[str] = Field(..., description="Algorithms used")
    has_complete_route: bool = Field(..., description="Whether route is complete")
    validation_status: str = Field(..., description="Validation status")
    trust_level: str = Field(..., description="Trust level")
    created_at: str = Field(..., description="Chain creation timestamp")
    last_modified: str = Field(..., description="Last modification timestamp")
    chain_hash: str = Field(..., description="Chain hash (truncated)")
    compliance_frameworks: List[str] = Field(..., description="Applicable frameworks")


class ModelPolicyValidation(BaseModel):
    """Policy validation result."""

    policy_id: str = Field(..., description="Policy identifier")
    policy_name: str = Field(..., description="Policy name")
    is_valid: bool = Field(..., description="Whether policy is satisfied")
    violations: List[str] = Field(default_factory=list, description="Policy violations")
    warnings: List[str] = Field(default_factory=list, description="Policy warnings")


class ModelSignatureVerificationResult(BaseModel):
    """Result of signature verification."""

    status: str = Field(..., description="Verification status")
    verified: bool = Field(..., description="Whether signatures are verified")
    signature_count: int = Field(..., description="Total signatures")
    verified_signatures: int = Field(..., description="Number of verified signatures")
    chain_validation: ModelChainValidation = Field(
        ..., description="Chain validation details"
    )
    policy_validation: Optional[ModelPolicyValidation] = Field(
        None, description="Policy validation if applicable"
    )
    verified_at: str = Field(..., description="Verification timestamp")
