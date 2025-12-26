"""
Detection Match Model.

Represents a single detection match within content during sensitive information detection.

Thread Safety
-------------
This model is immutable (frozen=True) and safe to share across threads after creation.
All fields are read-only once the instance is created.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod
from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_sensitivity_level import EnumSensitivityLevel
from omnibase_core.models.detection import ModelDetectionRuleMetadata

__all__ = [
    "ModelDetectionMatch",
]


class ModelDetectionMatch(BaseModel):
    """
    A single detection match within content.
    """

    start_position: int = Field(description="Start character position of the match")

    end_position: int = Field(description="End character position of the match")

    matched_text: str = Field(description="The actual text that was detected")

    redacted_text: str | None = Field(
        default=None,
        description="Redacted version of the matched text",
    )

    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score for this detection (0-1)",
    )

    detection_type: EnumDetectionType = Field(
        description="Type of sensitive information detected",
    )

    sensitivity_level: EnumSensitivityLevel = Field(
        description="Sensitivity level of the detected information",
    )

    detection_method: EnumDetectionMethod = Field(
        description="Method used to detect this information",
    )

    pattern_name: str | None = Field(
        default=None,
        description="Name of the pattern that matched",
    )

    context_before: str | None = Field(
        default=None,
        description="Text context before the match",
    )

    context_after: str | None = Field(
        default=None,
        description="Text context after the match",
    )

    metadata: ModelDetectionRuleMetadata | None = Field(
        default=None,
        description="Typed metadata for the detection rule that triggered this match",
    )

    model_config = ConfigDict(
        frozen=True,
        from_attributes=True,
        use_enum_values=True,
        extra="forbid",
    )
