"""
Progress Status Model - ONEX Standards Compliant.

Model for overall workflow progress status in the ONEX workflow coordination system.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .model_node_progress import ModelNodeProgress


class ModelProgressStatus(BaseModel):
    """Overall workflow progress status."""

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    overall_progress_percent: float = Field(
        ..., description="Overall workflow progress percentage", ge=0.0, le=100.0
    )

    current_stage: str = Field(..., description="Current stage of the workflow")

    stages_completed: int = Field(..., description="Number of stages completed", ge=0)

    stages_total: int = Field(
        ..., description="Total number of stages in the workflow", ge=1
    )

    estimated_completion: Optional[datetime] = Field(
        default=None, description="Estimated completion time"
    )

    node_progress: list[ModelNodeProgress] = Field(
        default_factory=list, description="Progress of individual nodes"
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
