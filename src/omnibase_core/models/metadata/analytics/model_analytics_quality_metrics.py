"""
Analytics Quality Metrics Model.

Quality and health metrics for analytics collections.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelAnalyticsQualityMetrics(BaseModel):
    """
    Quality and health metrics for analytics collections.

    Focused on quality indicators and health scoring.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Quality metrics
    health_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Overall health score (0-100)",
    )

    success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall success rate (0-1)",
    )

    documentation_coverage: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Documentation coverage (0-1)",
    )

    def is_healthy(self) -> bool:
        """Check if collection is healthy (health score > 80)."""
        return self.health_score > 80.0

    def has_good_success_rate(self) -> bool:
        """Check if collection has good success rate (> 90%)."""
        return self.success_rate > 0.9

    def has_good_documentation(self) -> bool:
        """Check if collection has good documentation coverage (> 70%)."""
        return self.documentation_coverage > 0.7

    def get_health_level(self) -> str:
        """Get descriptive health level."""
        if self.health_score >= 90.0:
            return "Excellent"
        if self.health_score >= 75.0:
            return "Good"
        if self.health_score >= 60.0:
            return "Fair"
        if self.health_score >= 40.0:
            return "Poor"
        return "Critical"

    def get_success_rate_percentage(self) -> float:
        """Get success rate as percentage."""
        return self.success_rate * 100.0

    def get_documentation_coverage_percentage(self) -> float:
        """Get documentation coverage as percentage."""
        return self.documentation_coverage * 100.0

    def update_quality_metrics(
        self,
        health_score: float,
        success_rate: float,
        documentation_coverage: float,
    ) -> None:
        """Update all quality metrics."""
        self.health_score = max(0.0, min(100.0, health_score))
        self.success_rate = max(0.0, min(1.0, success_rate))
        self.documentation_coverage = max(0.0, min(1.0, documentation_coverage))

    def calculate_composite_quality_score(self) -> float:
        """Calculate composite quality score (0-100)."""
        # Weight health score more heavily
        health_weight = 0.5
        success_weight = 0.3
        doc_weight = 0.2

        composite = (
            (self.health_score * health_weight)
            + (self.get_success_rate_percentage() * success_weight)
            + (self.get_documentation_coverage_percentage() * doc_weight)
        )

        return min(100.0, composite)

    def needs_attention(self) -> bool:
        """Check if quality metrics indicate attention is needed."""
        return (
            self.health_score < 70.0
            or self.success_rate < 0.8
            or self.documentation_coverage < 0.5
        )

    def get_improvement_suggestions(self) -> list[str]:
        """Get list of improvement suggestions based on metrics."""
        suggestions = []

        if self.health_score < 70.0:
            suggestions.append("Improve overall health score through error reduction")

        if self.success_rate < 0.8:
            suggestions.append("Increase success rate by fixing failing operations")

        if self.documentation_coverage < 0.5:
            suggestions.append("Improve documentation coverage")

        if self.health_score < 90.0 and self.success_rate > 0.9:
            suggestions.append(
                "Focus on health metrics while maintaining high success rate",
            )

        return suggestions

    @classmethod
    def create_excellent(cls) -> ModelAnalyticsQualityMetrics:
        """Create quality metrics with excellent scores."""
        return cls(
            health_score=95.0,
            success_rate=0.98,
            documentation_coverage=0.9,
        )

    @classmethod
    def create_good(cls) -> ModelAnalyticsQualityMetrics:
        """Create quality metrics with good scores."""
        return cls(
            health_score=82.0,
            success_rate=0.92,
            documentation_coverage=0.75,
        )

    @classmethod
    def create_needs_improvement(cls) -> ModelAnalyticsQualityMetrics:
        """Create quality metrics that need improvement."""
        return cls(
            health_score=65.0,
            success_rate=0.75,
            documentation_coverage=0.45,
        )

    model_config = ConfigDict(
        extra="ignore",
        from_attributes=True,
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Analytics models don't have standard name/description/version fields
        # Pack all quality metrics into metadata
        result["metadata"] = {
            "health_score": self.health_score,
            "success_rate": self.success_rate,
            "documentation_coverage": self.documentation_coverage,
            "health_level": self.get_health_level(),
            "composite_quality_score": self.calculate_composite_quality_score(),
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
__all__ = ["ModelAnalyticsQualityMetrics"]
