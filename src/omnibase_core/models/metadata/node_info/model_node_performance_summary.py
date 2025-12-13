"""
Node Performance Summary Model.

Structured performance summary data for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelNodePerformanceSummary(BaseModel):
    """
    Structured performance summary for nodes.

    Replaces primitive soup unions with typed fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Usage metrics
    usage_count: int = Field(description="Total usage count")
    success_rate_percentage: float = Field(description="Success rate as percentage")
    error_rate_percentage: float = Field(description="Error rate as percentage")

    # Performance metrics
    average_execution_time_ms: float = Field(
        description="Average execution time in milliseconds",
    )
    average_execution_time_seconds: float = Field(
        description="Average execution time in seconds",
    )
    memory_usage_mb: float = Field(description="Memory usage in MB")

    # Performance levels (string categories)
    performance_level: str = Field(description="Performance level category")
    reliability_level: str = Field(description="Reliability level category")
    memory_usage_level: str = Field(description="Memory usage level category")

    # Computed metrics
    performance_score: float = Field(description="Composite performance score (0-100)")

    # Boolean indicators
    has_performance_issues: bool = Field(
        description="Whether node has performance issues",
    )
    is_reliable: bool = Field(description="Whether node is reliable")

    # Improvement suggestions
    improvement_suggestions: list[str] = Field(
        default_factory=list,
        description="List of performance improvement suggestions",
    )

    @property
    def has_improvement_suggestions(self) -> bool:
        """Check if there are improvement suggestions available."""
        return len(self.improvement_suggestions) > 0

    @property
    def suggestion_count(self) -> int:
        """Get the number of improvement suggestions."""
        return len(self.improvement_suggestions)

    def get_overall_health_status(self) -> str:
        """Get overall health status based on multiple indicators."""
        if self.is_reliable and not self.has_performance_issues:
            return "Excellent"
        if self.is_reliable and self.has_performance_issues:
            return "Good"
        if not self.is_reliable and not self.has_performance_issues:
            return "Fair"
        return "Poor"

    def get_priority_improvements(self) -> list[str]:
        """Get the most critical improvement suggestions."""
        # Return up to 3 most important suggestions
        return self.improvement_suggestions[:3]

    @classmethod
    def create_summary(
        cls,
        usage_count: int,
        success_rate_percentage: float,
        error_rate_percentage: float,
        average_execution_time_ms: float,
        average_execution_time_seconds: float,
        memory_usage_mb: float,
        performance_level: str,
        reliability_level: str,
        memory_usage_level: str,
        performance_score: float,
        has_performance_issues: bool,
        is_reliable: bool,
        improvement_suggestions: list[str],
    ) -> ModelNodePerformanceSummary:
        """Create a performance summary with all required data."""
        return cls(
            usage_count=usage_count,
            success_rate_percentage=success_rate_percentage,
            error_rate_percentage=error_rate_percentage,
            average_execution_time_ms=average_execution_time_ms,
            average_execution_time_seconds=average_execution_time_seconds,
            memory_usage_mb=memory_usage_mb,
            performance_level=performance_level,
            reliability_level=reliability_level,
            memory_usage_level=memory_usage_level,
            performance_score=performance_score,
            has_performance_issues=has_performance_issues,
            is_reliable=is_reliable,
            improvement_suggestions=improvement_suggestions,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata  # type: ignore[return-value]

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
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
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelNodePerformanceSummary"]
