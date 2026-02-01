"""Model for pattern learning execution metadata."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.pattern_learning import EnumPatternLearningStatus
from omnibase_core.models.primitives import ModelSemVer


class ModelPatternLearningMetadata(BaseModel):
    """Metadata about pattern learning execution.

    Captures execution context for debugging and auditing.
    All timestamps should be in UTC.
    """

    status: EnumPatternLearningStatus = Field(
        description="Execution status of the pattern learning run"
    )
    model_version: ModelSemVer = Field(
        description="Semantic version of the learning model"
    )
    timestamp: datetime = Field(description="Execution timestamp (UTC)")
    deduplication_threshold_used: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity threshold for deduplication",
    )
    promotion_threshold_used: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence threshold for pattern promotion",
    )
    training_samples: int = Field(ge=0, description="Number of training samples")
    validation_samples: int = Field(ge=0, description="Number of validation samples")
    convergence_achieved: bool = Field(description="Whether training converged")
    early_stopped: bool = Field(description="Whether training stopped early")
    final_epoch: int = Field(ge=0, description="Final epoch number")

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )


__all__ = ["ModelPatternLearningMetadata"]
