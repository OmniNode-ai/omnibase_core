"""Policy Validation Model.

Policy validation result for signature verification.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelPolicyValidation(BaseModel):
    """Policy validation result.

    Note:
        This model uses frozen=True for immutability and from_attributes=True
        to support pytest-xdist parallel execution where class identity may
        differ between workers.
    """

    model_config = ConfigDict(frozen=True, from_attributes=True)

    policy_id: UUID = Field(default=..., description="Policy identifier")
    policy_name: str = Field(default=..., description="Policy name")
    is_valid: bool = Field(default=..., description="Whether policy is satisfied")
    violations: list[str] = Field(default_factory=list, description="Policy violations")
    warnings: list[str] = Field(default_factory=list, description="Policy warnings")
