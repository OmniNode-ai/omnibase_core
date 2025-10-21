from typing import Any

from pydantic import Field

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod
from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_sensitivity_level import EnumSensitivityLevel

from .model_detectionresult import ModelDetectionResult

"""
Detection result model for sensitive information detection.

Provides strongly-typed results from sensitive information detection operations.
"""

from enum import Enum

from pydantic import BaseModel, ConfigDict


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

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional detection metadata (string values only)",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
