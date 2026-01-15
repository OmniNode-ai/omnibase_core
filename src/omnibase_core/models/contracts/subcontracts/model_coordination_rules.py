"""
Coordination Rules Model.

Model for workflow coordination rules in the ONEX workflow coordination system.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelCoordinationRules(BaseModel):
    """Rules for workflow coordination."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    synchronization_points: list[str] = Field(
        default_factory=list,
        description="Named synchronization points in the workflow",
    )

    parallel_execution_allowed: bool = Field(
        default=True,
        description="Whether parallel execution is allowed",
    )

    failure_recovery_strategy: EnumFailureRecoveryStrategy = Field(
        default=EnumFailureRecoveryStrategy.RETRY,
        description="Strategy for handling failures",
    )

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        frozen=True,
        use_enum_values=False,
        validate_assignment=True,
    )
