"""
Velocity Log Model for tracking development productivity metrics.

This model represents a single velocity tracking entry that captures
timing, quality, and effectiveness metrics for agent tasks.
"""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.velocity.model_velocity_context import \
    ModelVelocityContext
from omnibase_core.model.velocity.model_velocity_metrics import \
    ModelVelocityMetrics


class ModelVelocityLog(BaseModel):
    """
    Complete velocity log entry for tracking agent productivity.

    This model captures all aspects of task execution including timing,
    quality metrics, context, and outcomes for learning and analysis.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    # Primary identification
    velocity_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique velocity log identifier",
    )
    agent_id: str = Field(description="ID of the agent performing the task")

    # Task information
    task_description: str = Field(description="Human-readable description of the task")
    task_type: str = Field(
        description="Type of task: implementation, debugging, analysis, documentation, etc."
    )

    # Timing information
    started_at: datetime = Field(description="When the task was started")
    completed_at: datetime = Field(description="When the task was completed")
    duration_seconds: float = Field(
        default=0.0, ge=0.0, description="Task duration in seconds (auto-calculated)"
    )

    # Outcome
    success: bool = Field(description="Whether the task was completed successfully")

    # Detailed metrics
    metrics: ModelVelocityMetrics = Field(
        default_factory=ModelVelocityMetrics, description="Detailed velocity metrics"
    )

    # Context information
    context: ModelVelocityContext = Field(
        default_factory=ModelVelocityContext, description="Task context information"
    )

    # Extensible metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for extensibility"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record last update timestamp"
    )

    def __post_init__(self):
        """Calculate duration automatically if not provided."""
        if self.duration_seconds == 0.0 and self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = delta.total_seconds()
