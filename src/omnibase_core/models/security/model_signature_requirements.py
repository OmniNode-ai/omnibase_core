from typing import Any

from pydantic import Field

"""
ModelSignatureRequirements: Signature requirements for policy evaluation.

This model defines the signature requirements evaluated by trust policies.
"""

from pydantic import BaseModel, Field

from .model_certificate_validation_level import ModelCertificateValidationLevel
from .model_trust_level import ModelTrustLevel


class ModelSignatureRequirements(BaseModel):
    """Signature requirements evaluated from policy rules."""

    minimum_signatures: int = Field(
        default=1,
        description="Minimum number of signatures required",
    )
    required_algorithms: list[str] = Field(
        default_factory=list,
        description="Required signature algorithms",
    )
    trusted_nodes: set[str] = Field(
        default_factory=set,
        description="Set of trusted node IDs",
    )
    compliance_tags: list[str] = Field(
        default_factory=list,
        description="Required compliance tags",
    )
    trust_level: ModelTrustLevel = Field(
        default_factory=lambda: ModelTrustLevel(level="standard"),
        description="Required trust level",
    )
    encryption_required: bool = Field(
        default=False,
        description="Whether encryption is required",
    )
    certificate_validation: ModelCertificateValidationLevel = Field(
        default_factory=lambda: ModelCertificateValidationLevel(level="standard"),
        description="Certificate validation level",
    )
    applicable_rules: list[str] = Field(
        default_factory=list,
        description="IDs of applicable policy rules",
    )
