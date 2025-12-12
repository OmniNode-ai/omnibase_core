"""
Detection Pattern Model.

Configuration for a single detection pattern used in sensitive information detection.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_detection_method import EnumDetectionMethod
from omnibase_core.enums.enum_detection_type import EnumDetectionType
from omnibase_core.enums.enum_language_code import EnumLanguageCode
from omnibase_core.enums.enum_sensitivity_level import EnumSensitivityLevel
from omnibase_core.models.security.model_security_summaries import (
    ModelDetectionPatternSummary,
)

__all__ = [
    "EnumLanguageCode",
    "ModelDetectionPattern",
]


class ModelDetectionPattern(BaseModel):
    """
    Configuration for a single detection pattern.
    """

    pattern_id: UUID = Field(description="Unique identifier for this pattern")
    pattern_name: str = Field(description="Human-readable name for this pattern")
    pattern_regex: str | None = Field(
        default=None,
        description="Regular expression pattern",
    )
    pattern_keywords: list[str] = Field(
        default_factory=list,
        description="Keywords to match",
    )
    detection_type: EnumDetectionType = Field(
        description="Type of sensitive information this pattern detects",
    )
    sensitivity_level: EnumSensitivityLevel = Field(
        description="Sensitivity level for matches from this pattern",
    )
    detection_method: EnumDetectionMethod = Field(
        description="Primary detection method for this pattern",
    )
    confidence_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for matches",
    )
    context_window_size: int = Field(
        default=50,
        ge=0,
        description="Size of context window around matches",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this pattern is currently enabled",
    )
    languages: list[EnumLanguageCode] = Field(
        default_factory=lambda: [EnumLanguageCode.ENGLISH],
        description="Languages this pattern supports",
    )
    false_positive_patterns: list[str] = Field(
        default_factory=list,
        description="Patterns to exclude as false positives",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example strings this pattern should match",
    )
    description: str | None = Field(
        default=None,
        description="Description of what this pattern detects",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )

    def is_enabled(self) -> bool:
        """Check if pattern is enabled."""
        return self.enabled

    def supports_language(self, language: EnumLanguageCode) -> bool:
        """Check if pattern supports a specific language."""
        return language in self.languages

    def meets_confidence_threshold(self, confidence: float) -> bool:
        """Check if confidence meets threshold."""
        return confidence >= self.confidence_threshold

    def get_summary(self) -> ModelDetectionPatternSummary:
        """Get pattern summary."""
        return ModelDetectionPatternSummary(
            pattern_id=self.pattern_id,
            pattern_name=self.pattern_name,
            detection_type=self.detection_type.value,
            sensitivity_level=self.sensitivity_level.value,
            enabled=self.enabled,
            supported_languages=[lang.value for lang in self.languages],
            confidence_threshold=self.confidence_threshold,
        )
