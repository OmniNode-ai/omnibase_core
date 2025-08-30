"""
Recommendation Model

Recommendation for document improvements.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_document_freshness_actions import (
    EnumEstimatedEffort, EnumRecommendationPriority, EnumRecommendationType)


class ModelRecommendation(BaseModel):
    """Recommendation for document improvements."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    type: EnumRecommendationType = Field(description="Type of recommendation")
    priority: EnumRecommendationPriority = Field(description="Priority level")
    target_files: List[str] = Field(description="Files affected by this recommendation")
    description: str = Field(
        min_length=1, description="Human-readable description of the recommendation"
    )
    action_items: List[str] = Field(
        description="Specific actions to address the recommendation"
    )
    estimated_effort: EnumEstimatedEffort = Field(
        description="Estimated effort to implement the recommendation"
    )
