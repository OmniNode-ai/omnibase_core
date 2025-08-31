"""
Change Detection Results Model

Results of change detection analysis.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.docs.model_change_item import ModelChangeItem


class ModelChangeDetectionResults(BaseModel):
    """Results of change detection analysis."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    changed_files: list[ModelChangeItem] = Field(description="Files that have changed")
    total_changes: int = Field(ge=0, description="Total number of changes detected")
    time_window: str = Field(description="Time window analyzed")
    analysis_timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the analysis was performed",
    )
