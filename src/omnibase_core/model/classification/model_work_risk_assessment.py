"""
Model for work risk assessment.

Complete risk assessment for a work item including characteristics,
risk factors, and execution recommendations.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.automation.model_work_metadata import ModelWorkMetadata
from omnibase_core.model.classification.enum_execution_mode import EnumExecutionMode
from omnibase_core.model.classification.enum_work_complexity import EnumWorkComplexity
from omnibase_core.model.classification.enum_work_priority import EnumWorkPriority
from omnibase_core.model.classification.enum_work_type import EnumWorkType
from omnibase_core.model.classification.model_risk_factors import ModelRiskFactors
from omnibase_core.model.classification.model_work_characteristics import (
    ModelWorkCharacteristics,
)


class ModelWorkRiskAssessment(BaseModel):
    """Complete risk assessment for a work item."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    work_item_id: str = Field(..., description="Unique identifier for work item")
    title: str = Field(..., description="Work item title")
    description: str | None = Field(None, description="Detailed description")

    work_type: EnumWorkType = Field(..., description="Type of work")
    complexity: EnumWorkComplexity = Field(..., description="Complexity level")
    priority: EnumWorkPriority = Field(..., description="Priority level")

    characteristics: ModelWorkCharacteristics = Field(
        ...,
        description="Work characteristics",
    )
    risk_factors: ModelRiskFactors = Field(..., description="Risk assessment factors")

    risk_score: float = Field(..., ge=0, le=10, description="Overall risk score (0-10)")
    confidence_score: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence in assessment",
    )

    recommended_execution: EnumExecutionMode = Field(
        ...,
        description="Recommended execution mode",
    )
    recommended_window: str | None = Field(
        None,
        description="Recommended time window",
    )

    overnight_safe: bool = Field(..., description="Safe for overnight execution")
    requires_human_review: bool = Field(..., description="Requires human review")

    similar_work_references: list[str] = Field(
        default_factory=list,
        description="References to similar completed work",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Work items that must complete first",
    )

    assessment_timestamp: datetime = Field(default_factory=datetime.utcnow)
    assessed_by: str = Field(
        "work_classifier",
        description="System that performed assessment",
    )

    metadata: ModelWorkMetadata | None = Field(
        default=None,
        description="Additional assessment data",
    )

    def is_low_risk(self) -> bool:
        """Check if work is low risk for autonomous execution."""
        return self.risk_score <= 3.0

    def is_high_risk(self) -> bool:
        """Check if work is high risk requiring human oversight."""
        return self.risk_score >= 7.0

    def can_execute_in_window(self, window_risk_threshold: str) -> bool:
        """Check if work can be executed in a window with given risk threshold."""
        risk_thresholds = {"low": 3.0, "medium": 5.0, "high": 7.0, "critical": 10.0}

        threshold = risk_thresholds.get(window_risk_threshold, 5.0)
        return self.risk_score <= threshold
