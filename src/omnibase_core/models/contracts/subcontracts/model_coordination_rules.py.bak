from typing import Any

from pydantic import Field

"""
Coordination Rules Model - ONEX Standards Compliant.

Model for workflow coordination rules in the ONEX workflow coordination system.
"""

from pydantic import BaseModel

from omnibase_core.enums.enum_workflow_coordination import EnumFailureRecoveryStrategy


class ModelCoordinationRules(BaseModel):
    """Rules for workflow coordination."""

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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
