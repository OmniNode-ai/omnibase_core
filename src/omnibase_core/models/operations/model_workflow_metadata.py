"""
Strongly-typed workflow metadata structure.

Replaces dict[str, Any] usage in workflow metadata with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from omnibase_core.core.decorators import allow_dict_str_any


class ModelWorkflowMetadata(BaseModel):
    """
    Strongly-typed workflow metadata.

    Replaces dict[str, Any] with structured workflow metadata model.
    """

    workflow_id: UUID = Field(
        default_factory=uuid4, description="Unique workflow identifier (UUID format)"
    )
    workflow_type: str = Field(..., description="Type of workflow")
    instance_id: UUID = Field(
        default_factory=uuid4, description="Workflow instance identifier (UUID format)"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="Last update timestamp"
    )

    # Workflow state
    current_step: str = Field(default="", description="Current workflow step")
    total_steps: int = Field(default=0, description="Total number of steps")
    completed_steps: int = Field(default=0, description="Number of completed steps")

    # Dependencies
    parent_workflow_id: UUID | None = Field(
        default=None, description="Parent workflow identifier (UUID format)"
    )
    dependency_count: int = Field(default=0, description="Number of dependencies")

    # Tags and labels
    tags: dict[str, str] = Field(default_factory=dict, description="Workflow tags")
    labels: dict[str, str] = Field(default_factory=dict, description="Workflow labels")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export for use
__all__ = ["ModelWorkflowMetadata"]
