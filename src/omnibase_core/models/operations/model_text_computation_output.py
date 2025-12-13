"""
Text Computation Output Model.

Text computation output data with language detection and confidence scores.
"""

from pydantic import Field

from omnibase_core.enums.enum_computation_type import EnumComputationType
from omnibase_core.models.operations.model_computation_output_base import (
    ModelComputationOutputBase,
)
from omnibase_core.types.typed_dict_text_computation_summary import (
    TypedDictTextComputationSummary,
)


class ModelTextComputationOutput(ModelComputationOutputBase):
    """Text computation output data."""

    computation_type: EnumComputationType = Field(
        default=EnumComputationType.TEXT,
        description="Text computation type",
    )
    text_results: dict[str, str] = Field(
        default_factory=dict,
        description="Text computation results",
    )
    language_detected: str = Field(
        default="",
        description="Detected language of processed text",
    )
    confidence_scores: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence scores for text analysis",
    )
    processing_warnings: list[str] = Field(
        default_factory=list,
        description="Any processing warnings encountered",
    )

    def add_text_result(self, key: str, value: str) -> "ModelTextComputationOutput":
        """Add a text result."""
        new_results = {**self.text_results, key: value}
        return self.model_copy(update={"text_results": new_results})

    def get_text_result(self, key: str) -> str | None:
        """Get a text result by key."""
        return self.text_results.get(key)

    def set_language_detected(self, language: str) -> "ModelTextComputationOutput":
        """Set the detected language."""
        return self.model_copy(update={"language_detected": language})

    def add_confidence_score(
        self, key: str, score: float
    ) -> "ModelTextComputationOutput":
        """Add a confidence score."""
        new_scores = {**self.confidence_scores, key: score}
        return self.model_copy(update={"confidence_scores": new_scores})

    def get_confidence_score(self, key: str) -> float | None:
        """Get a confidence score by key."""
        return self.confidence_scores.get(key)

    def get_average_confidence(self) -> float:
        """Get average confidence score."""
        if not self.confidence_scores:
            return 0.0
        return sum(self.confidence_scores.values()) / len(self.confidence_scores)

    def add_processing_warning(self, warning: str) -> "ModelTextComputationOutput":
        """Add a processing warning."""
        new_warnings = [*self.processing_warnings, warning]
        return self.model_copy(update={"processing_warnings": new_warnings})

    def has_processing_warnings(self) -> bool:
        """Check if there are any processing warnings."""
        return len(self.processing_warnings) > 0

    def get_text_summary(self) -> TypedDictTextComputationSummary:
        """Get text processing summary."""
        return TypedDictTextComputationSummary(
            language_detected=self.language_detected,
            result_count=len(self.text_results),
            average_confidence=self.get_average_confidence(),
            has_warnings=self.has_processing_warnings(),
            warning_count=len(self.processing_warnings),
        )
