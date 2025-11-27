from uuid import UUID

from pydantic import Field

"\nModelPolicyValidationResult: Result of policy validation against signature chain.\n\nThis model represents the result of validating a signature chain against a trust policy.\n"
from pydantic import BaseModel

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_policy_severity import ModelPolicySeverity
from .model_signature_requirements import ModelSignatureRequirements


class ModelPolicyValidationResult(BaseModel):
    """Result of policy validation against a signature chain."""

    policy_id: UUID = Field(
        default=..., description="ID of the policy that was evaluated"
    )
    policy_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the policy",
    )
    status: str = Field(
        default=..., description="Validation status: compliant, warning, violated"
    )
    severity: ModelPolicySeverity = Field(
        default=..., description="Severity level of any violations"
    )
    violations: list[str] = Field(
        default_factory=list, description="List of policy violations"
    )
    warnings: list[str] = Field(
        default_factory=list, description="List of policy warnings"
    )
    requirements: ModelSignatureRequirements = Field(
        default=..., description="Evaluated signature requirements"
    )
    enforcement_mode: str = Field(default=..., description="Policy enforcement mode")
    validated_at: str = Field(default=..., description="Timestamp of validation")
