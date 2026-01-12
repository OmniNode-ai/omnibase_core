"""
Progress Status Model.

Model for overall workflow progress status in the ONEX workflow coordination system.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

from .model_node_progress import ModelNodeProgress


class ModelProgressStatus(BaseModel):
    """Overall workflow progress status."""

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

    workflow_id: UUID = Field(default_factory=uuid4, description="Workflow identifier")

    overall_progress_percent: float = Field(
        default=...,
        description="Overall workflow progress percentage",
        ge=0.0,
        le=100.0,
    )

    current_stage: str = Field(default=..., description="Current stage of the workflow")

    stages_completed: int = Field(
        default=..., description="Number of stages completed", ge=0
    )

    stages_total: int = Field(
        default=..., description="Total number of stages in the workflow", ge=1
    )

    estimated_completion: datetime | None = Field(
        default=None, description="Estimated completion time"
    )

    node_progress: list[ModelNodeProgress] = Field(
        default_factory=list, description="Progress of individual nodes"
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
