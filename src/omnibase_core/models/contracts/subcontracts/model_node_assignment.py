"""
Node Assignment Model.

Model for node assignment in workflow execution for the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumAssignmentStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_resource_usage_metric import ModelResourceUsageMetric


class ModelNodeAssignment(BaseModel):
    """Node assignment for workflow execution."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    node_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the node",
    )

    node_type: EnumNodeType = Field(default=..., description="Type of the node")

    assignment_status: EnumAssignmentStatus = Field(
        default=...,
        description="Current status of the assignment",
    )

    execution_time_ms: int = Field(
        default=0,
        description="Time spent executing on this node in milliseconds",
        ge=0,
    )

    resource_usage: list[ModelResourceUsageMetric] = Field(
        default_factory=list,
        description="Strongly-typed resource usage metrics for this node",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
