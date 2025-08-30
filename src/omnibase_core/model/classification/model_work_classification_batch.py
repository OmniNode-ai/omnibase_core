"""
Model for work classification batch.

Batch of work items with classification results.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.automation.model_batch_statistics import ModelBatchStatistics
from omnibase_core.model.classification.enum_work_priority import EnumWorkPriority
from omnibase_core.model.classification.model_work_risk_assessment import (
    ModelWorkRiskAssessment,
)


class ModelWorkClassificationBatch(BaseModel):
    """Batch of work items with classification results."""

    batch_id: str = Field(..., description="Unique batch identifier")
    total_items: int = Field(..., ge=0, description="Total items in batch")

    overnight_safe_items: list[ModelWorkRiskAssessment] = Field(
        default_factory=list,
        description="Items safe for overnight execution",
    )

    day_shift_items: list[ModelWorkRiskAssessment] = Field(
        default_factory=list,
        description="Items requiring day shift attention",
    )

    human_only_items: list[ModelWorkRiskAssessment] = Field(
        default_factory=list,
        description="Items requiring human execution",
    )

    deferred_items: list[ModelWorkRiskAssessment] = Field(
        default_factory=list,
        description="Items deferred for later",
    )

    classification_timestamp: datetime = Field(default_factory=datetime.utcnow)

    statistics: ModelBatchStatistics | None = Field(
        default=None,
        description="Batch classification statistics",
    )

    def get_window_allocations(self) -> dict[str, list[str]]:
        """Get work items allocated to each execution window."""
        allocations = {
            "window_1_prime": [],
            "window_2_night": [],
            "window_3_morning": [],
            "window_4_day": [],
            "window_5_planning": [],
        }

        # Allocate based on priority and risk
        for item in self.overnight_safe_items:
            if item.priority in (EnumWorkPriority.URGENT, EnumWorkPriority.HIGH):
                allocations["window_1_prime"].append(item.work_item_id)
            else:
                allocations["window_2_night"].append(item.work_item_id)

        for item in self.day_shift_items:
            if item.priority == EnumWorkPriority.URGENT:
                allocations["window_3_morning"].append(item.work_item_id)
            else:
                allocations["window_4_day"].append(item.work_item_id)

        return allocations
