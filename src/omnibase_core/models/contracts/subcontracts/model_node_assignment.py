import uuid
from typing import Any

from pydantic import Field

"""
Node Assignment Model - ONEX Standards Compliant.

Model for node assignment in workflow execution for the ONEX workflow coordination system.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.enums.enum_workflow_coordination import EnumAssignmentStatus


class ModelNodeAssignment(BaseModel):
    """Node assignment for workflow execution."""

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

    resource_usage: dict[str, float] = Field(
        default_factory=dict,
        description="Resource usage metrics for this node",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
