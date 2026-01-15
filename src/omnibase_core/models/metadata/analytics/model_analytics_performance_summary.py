"""
Analytics Performance Summary Model.

Structured performance summary data for analytics.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel


class ModelAnalyticsPerformanceSummary(BaseModel):
    """
    Structured performance summary for analytics.

    Replaces primitive soup unions with typed fields.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Performance metrics
    average_execution_time_ms: float = Field(
        description="Average execution time in milliseconds",
    )
    average_execution_time_seconds: float = Field(
        description="Average execution time in seconds",
    )
    peak_memory_usage_mb: float = Field(description="Peak memory usage in MB")

    # Count metrics
    total_invocations: int = Field(description="Total number of invocations")

    # Performance levels (string categories)
    performance_level: str = Field(description="Performance level category")
    memory_usage_level: str = Field(description="Memory usage level category")

    # Computed metrics
    performance_score: float = Field(description="Composite performance score")

    # Boolean indicators
    needs_optimization: bool = Field(description="Whether optimization is needed")

    @property
    def has_invocation_data(self) -> bool:
        """Check if there are any invocations recorded."""
        return self.total_invocations > 0

    @property
    def is_fast_performance(self) -> bool:
        """Check if performance is considered fast (< 100ms)."""
        return self.average_execution_time_ms < 100.0

    @property
    def is_low_memory_usage(self) -> bool:
        """Check if memory usage is low (< 10MB)."""
        return self.peak_memory_usage_mb < 10.0

    def get_overall_performance_status(self) -> str:
        """Get overall performance status based on multiple indicators."""
        if self.is_fast_performance and self.is_low_memory_usage:
            return "Excellent"
        if self.is_fast_performance or self.is_low_memory_usage:
            return "Good"
        if not self.needs_optimization:
            return "Fair"
        return "Poor"

    def get_performance_metrics(self) -> dict[str, float]:
        """Get core performance metrics as a dictionary."""
        return {
            "execution_time_ms": self.average_execution_time_ms,
            "execution_time_seconds": self.average_execution_time_seconds,
            "memory_usage_mb": self.peak_memory_usage_mb,
            "performance_score": self.performance_score,
        }

    @classmethod
    def create_summary(
        cls,
        average_execution_time_ms: float,
        average_execution_time_seconds: float,
        peak_memory_usage_mb: float,
        total_invocations: int,
        performance_level: str,
        memory_usage_level: str,
        performance_score: float,
        needs_optimization: bool,
    ) -> ModelAnalyticsPerformanceSummary:
        """Create a performance summary with all required data."""
        return cls(
            average_execution_time_ms=average_execution_time_ms,
            average_execution_time_seconds=average_execution_time_seconds,
            peak_memory_usage_mb=peak_memory_usage_mb,
            total_invocations=total_invocations,
            performance_level=performance_level,
            memory_usage_level=memory_usage_level,
            performance_score=performance_score,
            needs_optimization=needs_optimization,
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
        # Pack all performance summary data into metadata
        result["metadata"] = {
            "average_execution_time_ms": self.average_execution_time_ms,
            "average_execution_time_seconds": self.average_execution_time_seconds,
            "peak_memory_usage_mb": self.peak_memory_usage_mb,
            "total_invocations": self.total_invocations,
            "performance_level": self.performance_level,
            "memory_usage_level": self.memory_usage_level,
            "performance_score": self.performance_score,
            "needs_optimization": self.needs_optimization,
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If metadata setting logic fails
        """
        for key, value in metadata.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            Exception: If validation logic fails
        """
        # Basic validation - ensure required fields exist
        # Override in specific models for custom validation
        return True


# Export for use
__all__ = ["ModelAnalyticsPerformanceSummary"]
