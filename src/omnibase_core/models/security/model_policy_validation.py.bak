"""Policy Validation Model.

Policy validation result for signature verification.
"""

from pydantic import BaseModel, Field


class ModelPolicyValidation(BaseModel):
    """Policy validation result."""

    policy_id: str = Field(..., description="Policy identifier")
    policy_name: str = Field(..., description="Policy name")
    is_valid: bool = Field(..., description="Whether policy is satisfied")
    violations: list[str] = Field(default_factory=list, description="Policy violations")
    warnings: list[str] = Field(default_factory=list, description="Policy warnings")
