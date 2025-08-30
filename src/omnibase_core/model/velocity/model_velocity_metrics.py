"""
Velocity Metrics Model for detailed task performance measurements.

This model captures detailed metrics about agent task performance
using existing ONEX metric infrastructure and tool models.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.ai_workflows.model_ai_execution_metrics import (
    EnumMetricType,
    EnumMetricUnit,
    ModelMetricValue,
)
from omnibase_core.model.core.model_tool_type import ModelToolType


class ModelVelocityMetrics(BaseModel):
    """Detailed velocity metrics for task analysis using ONEX metric standards."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True)

    # Performance metrics
    lines_of_code_changed: int = Field(
        default=0,
        ge=0,
        description="Number of lines of code modified",
    )
    files_modified: int = Field(
        default=0,
        ge=0,
        description="Number of files that were changed",
    )
    tools_used: list[ModelToolType] = Field(
        default_factory=list,
        description="List of ONEX tools used during the task",
    )

    # Quality metrics using standardized metric values
    complexity_metric: ModelMetricValue = Field(
        default_factory=lambda: ModelMetricValue(
            name="task_complexity",
            value=0.0,
            unit=EnumMetricUnit.SCORE_0_TO_1,
            type=EnumMetricType.QUALITY,
        ),
        description="Task complexity score using standard metric format",
    )

    effectiveness_metric: ModelMetricValue = Field(
        default_factory=lambda: ModelMetricValue(
            name="task_effectiveness",
            value=0.0,
            unit=EnumMetricUnit.SCORE_0_TO_1,
            type=EnumMetricType.QUALITY,
        ),
        description="Task effectiveness score using standard metric format",
    )

    # Context metrics
    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of errors encountered",
    )
    retry_count: int = Field(default=0, ge=0, description="Number of retries required")
    validation_passes: int = Field(
        default=0,
        ge=0,
        description="Number of validation checks that passed",
    )

    # Additional standardized metrics
    additional_metrics: list[ModelMetricValue] = Field(
        default_factory=list,
        description="Additional metrics using ONEX metric format",
    )

    # Extensible metadata for custom data
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata for extensibility",
    )
