"""
Core Workflow Model.

Base model for workflow definitions and execution tracking in the ONEX system.
Used across the workflow coordination, execution, and monitoring subsystems.

Strict typing is enforced: No Any types allowed.
"""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import (
    MAX_DESCRIPTION_LENGTH,
    MAX_ERROR_MESSAGE_LENGTH,
    MAX_IDENTIFIER_LENGTH,
    MAX_NAME_LENGTH,
)
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelWorkflow(BaseModel):
    """
    Core workflow model for ONEX workflow system.

    Represents a workflow definition with execution tracking capabilities.
    Used by workflow coordination, metrics collection, and execution systems.

    Strict typing is enforced: No Any types allowed.
    """

    workflow_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this workflow",
    )

    name: str = Field(
        default=...,
        description="Human-readable workflow name",
        min_length=1,
        max_length=MAX_NAME_LENGTH,
    )

    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Semantic version of this workflow",
    )

    description: str = Field(
        default="",
        description="Detailed description of workflow purpose and behavior",
        max_length=MAX_DESCRIPTION_LENGTH,
    )

    category: str = Field(
        default="general",
        description="Workflow category for organization and filtering",
        max_length=MAX_IDENTIFIER_LENGTH,
    )

    status: EnumWorkflowStatus = Field(
        default=EnumWorkflowStatus.PENDING,
        description="Current execution status of the workflow",
    )

    steps_total: int = Field(
        default=0,
        description="Total number of steps in the workflow",
        ge=0,
    )

    steps_completed: int = Field(
        default=0,
        description="Number of completed workflow steps",
        ge=0,
    )

    timeout_ms: int = Field(
        default=600000,
        description="Workflow timeout in milliseconds (default: 10 minutes)",
        ge=1000,
        le=3600000,  # Max 1 hour
    )

    estimated_duration_ms: int | None = Field(
        default=None,
        description="Estimated duration in milliseconds",
        ge=0,
    )

    created_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when workflow was created",
    )

    started_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when workflow started execution",
    )

    completed_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp when workflow completed",
    )

    last_updated_at: str | None = Field(
        default=None,
        description="ISO 8601 timestamp of last status update",
    )

    error_message: str | None = Field(
        default=None,
        description="Error message if workflow failed",
        max_length=MAX_ERROR_MESSAGE_LENGTH,
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )


__all__ = ["ModelWorkflow"]
