"""
Node Quality Indicators Model.

Quality and documentation indicators for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_documentation_quality import EnumDocumentationQuality
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_node_quality_summary import ModelNodeQualitySummary


class ModelNodeQualityIndicators(BaseModel):
    """
    Node quality and documentation indicators.

    Focused on quality assessment and documentation tracking.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Quality indicators
    has_documentation: bool = Field(default=False, description="Has documentation")
    has_examples: bool = Field(default=False, description="Has examples")
    documentation_quality: EnumDocumentationQuality = Field(
        default=EnumDocumentationQuality.UNKNOWN,
        description="Documentation quality level",
    )

    @property
    def is_well_documented(self) -> bool:
        """Check if node is well documented."""
        return self.has_documentation and self.documentation_quality in [
            EnumDocumentationQuality.GOOD,
            EnumDocumentationQuality.EXCELLENT,
        ]

    @property
    def needs_documentation(self) -> bool:
        """Check if node needs documentation."""
        return not self.has_documentation or self.documentation_quality in [
            EnumDocumentationQuality.UNKNOWN,
            EnumDocumentationQuality.POOR,
        ]

    @property
    def has_complete_quality_info(self) -> bool:
        """Check if quality information is complete."""
        return (
            self.has_documentation
            and self.documentation_quality != EnumDocumentationQuality.UNKNOWN
        )

    def get_documentation_quality_level(self) -> str:
        """Get descriptive documentation quality level."""
        return self.documentation_quality.value

    def get_quality_score(self) -> float:
        """Calculate quality score (0-100)."""
        score = 0.0

        # Base score for having documentation
        if self.has_documentation:
            score += 40.0

        # Additional score for documentation quality
        quality_scores = {
            EnumDocumentationQuality.EXCELLENT: 40.0,
            EnumDocumentationQuality.GOOD: 30.0,
            EnumDocumentationQuality.ADEQUATE: 20.0,
            EnumDocumentationQuality.POOR: 5.0,
            EnumDocumentationQuality.UNKNOWN: 0.0,
        }
        score += quality_scores.get(self.documentation_quality, 0.0)

        # Bonus for having examples
        if self.has_examples:
            score += 20.0

        return min(100.0, score)

    def get_quality_level(self) -> str:
        """Get descriptive quality level."""
        score = self.get_quality_score()
        if score >= 90.0:
            return "Excellent"
        if score >= 75.0:
            return "Good"
        if score >= 60.0:
            return "Fair"
        if score >= 40.0:
            return "Poor"
        return "Needs Improvement"

    def update_documentation_status(
        self,
        has_documentation: bool,
        quality: EnumDocumentationQuality | None = None,
        has_examples: bool | None = None,
    ) -> None:
        """Update documentation status."""
        self.has_documentation = has_documentation
        if quality is not None:
            self.documentation_quality = quality
        if has_examples is not None:
            self.has_examples = has_examples

    def set_documentation_quality(self, quality: EnumDocumentationQuality) -> None:
        """Set documentation quality level."""
        self.documentation_quality = quality
        # If quality is set to something other than UNKNOWN, assume documentation exists
        if quality != EnumDocumentationQuality.UNKNOWN:
            self.has_documentation = True

    def add_documentation(
        self,
        quality: EnumDocumentationQuality = EnumDocumentationQuality.ADEQUATE,
    ) -> None:
        """Mark node as having documentation."""
        self.has_documentation = True
        self.documentation_quality = quality

    def add_examples(self) -> None:
        """Mark node as having examples."""
        self.has_examples = True

    def remove_documentation(self) -> None:
        """Mark node as not having documentation."""
        self.has_documentation = False
        self.documentation_quality = EnumDocumentationQuality.UNKNOWN
        self.has_examples = False

    def get_improvement_suggestions(self) -> list[str]:
        """Get list[Any]of improvement suggestions."""
        suggestions = []

        if not self.has_documentation:
            suggestions.append("Add documentation")

        if self.has_documentation and self.documentation_quality in [
            EnumDocumentationQuality.POOR,
            EnumDocumentationQuality.UNKNOWN,
        ]:
            suggestions.append("Improve documentation quality")

        if not self.has_examples:
            suggestions.append("Add usage examples")

        if self.documentation_quality == EnumDocumentationQuality.ADEQUATE:
            suggestions.append("Consider enhancing documentation to good quality")

        return suggestions

    def get_quality_summary(self) -> ModelNodeQualitySummary:
        """Get comprehensive quality summary."""
        return ModelNodeQualitySummary.create_summary(
            has_documentation=self.has_documentation,
            has_examples=self.has_examples,
            documentation_quality=self.documentation_quality.value,
            quality_score=self.get_quality_score(),
            quality_level=self.get_quality_level(),
            is_well_documented=self.is_well_documented,
            needs_documentation=self.needs_documentation,
            improvement_suggestions=self.get_improvement_suggestions(),
        )

    @classmethod
    def create_undocumented(cls) -> ModelNodeQualityIndicators:
        """Create quality indicators for undocumented node."""
        return cls()

    @classmethod
    def create_well_documented(cls) -> ModelNodeQualityIndicators:
        """Create quality indicators for well-documented node."""
        return cls(
            has_documentation=True,
            has_examples=True,
            documentation_quality=EnumDocumentationQuality.GOOD,
        )

    @classmethod
    def create_excellent_quality(cls) -> ModelNodeQualityIndicators:
        """Create quality indicators with excellent quality."""
        return cls(
            has_documentation=True,
            has_examples=True,
            documentation_quality=EnumDocumentationQuality.EXCELLENT,
        )

    @classmethod
    def create_with_quality(
        cls,
        has_documentation: bool,
        quality: EnumDocumentationQuality,
        has_examples: bool = False,
    ) -> ModelNodeQualityIndicators:
        """Create quality indicators with specific quality level."""
        return cls(
            has_documentation=has_documentation,
            has_examples=has_examples,
            documentation_quality=quality,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Pack quality indicator fields into metadata dict
        # Convert list[str] to list for JsonType compatibility
        result["metadata"] = {
            "has_documentation": self.has_documentation,
            "has_examples": self.has_examples,
            "documentation_quality": self.documentation_quality.value,
            "is_well_documented": self.is_well_documented,
            "needs_documentation": self.needs_documentation,
            "quality_score": self.get_quality_score(),
            "quality_level": self.get_quality_level(),
            "improvement_suggestions": list(self.get_improvement_suggestions()),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelNodeQualityIndicators"]
