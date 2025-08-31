"""
Success criteria model - Strongly typed success criteria structure.

Replaces Dict[str, Any] usage with strongly typed success criteria information.
"""

from pydantic import BaseModel, Field


class ModelSuccessCriteria(BaseModel):
    """Strongly typed success criteria."""

    primary_metric: str = Field(description="Primary success metric name")
    primary_threshold: float = Field(description="Primary metric threshold value")
    secondary_metrics: list[str] = Field(
        default_factory=list,
        description="Secondary success metrics",
    )
    secondary_thresholds: list[float] = Field(
        default_factory=list,
        description="Secondary metric thresholds",
    )
    quality_gates: list[str] = Field(
        default_factory=list,
        description="Quality gates that must pass",
    )
    failure_conditions: list[str] = Field(
        default_factory=list,
        description="Conditions that indicate failure",
    )
    timeout_seconds: int | None = Field(
        default=None,
        description="Timeout for success evaluation",
    )
    evaluation_mode: str = Field(
        default="all_pass",
        description="How to evaluate multiple criteria",
    )
