"""
Model for learning trends analysis in debug intelligence system.

This model represents learning trend analysis for agent performance
over time to identify improvement patterns.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TrendDirection(str, Enum):
    """Trend direction enumeration."""

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class ModelLearningTrends(BaseModel):
    """Model for learning trends analysis."""

    trend: TrendDirection = Field(description="Overall trend direction")
    recent_success_rate: Optional[float] = Field(
        default=None, description="Success rate of recent attempts"
    )
    older_success_rate: Optional[float] = Field(
        default=None, description="Success rate of older attempts"
    )
    improvement_rate: Optional[float] = Field(
        default=None, description="Rate of improvement (positive means improving)"
    )
    consistency_score: Optional[float] = Field(
        default=None, description="Consistency score (0.0 to 1.0)"
    )
    total_attempts_analyzed: int = Field(
        description="Total number of attempts analyzed"
    )
    trend_confidence: Optional[float] = Field(
        default=None, description="Confidence in the trend analysis (0.0 to 1.0)"
    )
