"""Workflow request model for Reducer Pattern Engine."""

import re
from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from .model_workflow_types import WorkflowType


class ModelWorkflowRequest(BaseModel):
    """
    Request model for workflow processing.

    Contains all necessary information for routing and processing
    a workflow through the Reducer Pattern Engine.
    """

    workflow_id: UUID = Field(
        default_factory=uuid4, description="Unique workflow identifier"
    )
    workflow_type: WorkflowType = Field(..., description="Type of workflow to process")
    instance_id: str = Field(
        ...,
        description="Unique instance identifier for isolation",
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$",
    )
    correlation_id: UUID = Field(
        default_factory=uuid4, description="Correlation ID for tracking"
    )
    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow data payload"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Workflow metadata"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Request creation timestamp"
    )

    @field_validator("instance_id")
    @classmethod
    def validate_instance_id(cls, v: str) -> str:
        """
        Validate instance_id format and constraints.

        Rules:
        - Length: 1-128 characters
        - Format: alphanumeric, hyphens, underscores only
        - Must start and end with alphanumeric character (unless single char)
        - Cannot be empty or only whitespace

        Args:
            v: The instance_id value to validate

        Returns:
            str: The validated instance_id

        Raises:
            ValueError: If validation fails
        """
        if not v or v.isspace():
            raise ValueError("instance_id cannot be empty or only whitespace")

        v = v.strip()

        if len(v) < 1 or len(v) > 128:
            raise ValueError("instance_id must be between 1 and 128 characters")

        # Check pattern: alphanumeric start/end, alphanumeric/hyphens/underscores in middle
        pattern = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$")
        if not pattern.match(v):
            raise ValueError(
                "instance_id must contain only alphanumeric characters, hyphens, and underscores. "
                "Must start and end with alphanumeric characters."
            )

        return v

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str,
        }
