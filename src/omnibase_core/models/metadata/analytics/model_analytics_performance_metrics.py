"""
Analytics Performance Metrics Model.

Performance and execution metrics for analytics collections.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_analytics_performance_summary import ModelAnalyticsPerformanceSummary


class ModelAnalyticsPerformanceMetrics(BaseModel):
    """
    Performance and execution metrics for analytics collections.

    Focused on timing, memory usage, and invocation tracking.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Performance metrics
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
    )

    peak_memory_usage_mb: float = Field(
        default=0.0,
        description="Peak memory usage in MB",
    )

    total_invocations: int = Field(default=0, description="Total number of invocations")

    @property
    def average_execution_time_seconds(self) -> float:
        """Get average execution time in seconds."""
        return self.average_execution_time_ms / 1000.0

    @property
    def has_performance_data(self) -> bool:
        """Check if performance data is available."""
        return self.total_invocations > 0

    def is_fast_execution(self, threshold_ms: float = 100.0) -> bool:
        """Check if execution time is below threshold."""
        return self.average_execution_time_ms <= threshold_ms

    def is_memory_efficient(self, threshold_mb: float = 100.0) -> bool:
        """Check if memory usage is below threshold."""
        return self.peak_memory_usage_mb <= threshold_mb

    def get_performance_level(self) -> str:
        """Get descriptive performance level."""
        if self.average_execution_time_ms <= 50.0:
            return "Excellent"
        if self.average_execution_time_ms <= 100.0:
            return "Good"
        if self.average_execution_time_ms <= 250.0:
            return "Fair"
        if self.average_execution_time_ms <= 500.0:
            return "Poor"
        return "Critical"

    def get_memory_usage_level(self) -> str:
        """Get descriptive memory usage level."""
        if self.peak_memory_usage_mb <= 50.0:
            return "Low"
        if self.peak_memory_usage_mb <= 100.0:
            return "Moderate"
        if self.peak_memory_usage_mb <= 250.0:
            return "High"
        return "Very High"

    def calculate_throughput_per_second(self, time_window_seconds: float) -> float:
        """Calculate throughput (invocations per second)."""
        if time_window_seconds <= 0:
            return 0.0
        return self.total_invocations / time_window_seconds

    def calculate_performance_score(self) -> float:
        """Calculate composite performance score (0-100)."""
        # Score based on execution time (lower is better)
        if self.average_execution_time_ms <= 50.0:
            time_score = 100.0
        elif self.average_execution_time_ms <= 100.0:
            time_score = 85.0
        elif self.average_execution_time_ms <= 250.0:
            time_score = 70.0
        elif self.average_execution_time_ms <= 500.0:
            time_score = 50.0
        else:
            time_score = 25.0

        # Score based on memory usage (lower is better)
        if self.peak_memory_usage_mb <= 50.0:
            memory_score = 100.0
        elif self.peak_memory_usage_mb <= 100.0:
            memory_score = 85.0
        elif self.peak_memory_usage_mb <= 250.0:
            memory_score = 70.0
        else:
            memory_score = 50.0

        # Weighted average (execution time is more important)
        return (time_score * 0.7) + (memory_score * 0.3)

    def needs_optimization(self) -> bool:
        """Check if performance metrics indicate optimization is needed."""
        return (
            self.average_execution_time_ms > 200.0 or self.peak_memory_usage_mb > 200.0
        )

    def update_performance_metrics(
        self,
        avg_execution_time_ms: float,
        peak_memory_mb: float,
        total_invocations: int,
    ) -> None:
        """Update all performance metrics."""
        self.average_execution_time_ms = max(0.0, avg_execution_time_ms)
        self.peak_memory_usage_mb = max(0.0, peak_memory_mb)
        self.total_invocations = max(0, total_invocations)

    def add_execution_sample(
        self,
        execution_time_ms: float,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Add a new execution sample and update averages."""
        if self.total_invocations == 0:
            self.average_execution_time_ms = execution_time_ms
        else:
            # Update running average
            total_time = self.average_execution_time_ms * self.total_invocations
            total_time += execution_time_ms
            self.average_execution_time_ms = total_time / (self.total_invocations + 1)

        # Update peak memory usage
        self.peak_memory_usage_mb = max(memory_usage_mb, self.peak_memory_usage_mb)

        self.total_invocations += 1

    def get_performance_summary(self) -> ModelAnalyticsPerformanceSummary:
        """Get comprehensive performance summary."""
        return ModelAnalyticsPerformanceSummary.create_summary(
            average_execution_time_ms=self.average_execution_time_ms,
            average_execution_time_seconds=self.average_execution_time_seconds,
            peak_memory_usage_mb=self.peak_memory_usage_mb,
            total_invocations=self.total_invocations,
            performance_level=self.get_performance_level(),
            memory_usage_level=self.get_memory_usage_level(),
            performance_score=self.calculate_performance_score(),
            needs_optimization=self.needs_optimization(),
        )

    @classmethod
    def create_fast(cls) -> ModelAnalyticsPerformanceMetrics:
        """Create performance metrics with fast execution."""
        return cls(
            average_execution_time_ms=25.0,
            peak_memory_usage_mb=30.0,
            total_invocations=1000,
        )

    @classmethod
    def create_slow(cls) -> ModelAnalyticsPerformanceMetrics:
        """Create performance metrics with slow execution."""
        return cls(
            average_execution_time_ms=750.0,
            peak_memory_usage_mb=300.0,
            total_invocations=100,
        )

    @classmethod
    def create_with_metrics(
        cls,
        avg_execution_time_ms: float,
        peak_memory_mb: float,
        total_invocations: int,
    ) -> ModelAnalyticsPerformanceMetrics:
        """Create performance metrics with specified values."""
        return cls(
            average_execution_time_ms=avg_execution_time_ms,
            peak_memory_usage_mb=peak_memory_mb,
            total_invocations=total_invocations,
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
        # Pack all performance metrics into metadata
        result["metadata"] = {
            "average_execution_time_ms": self.average_execution_time_ms,
            "peak_memory_usage_mb": self.peak_memory_usage_mb,
            "total_invocations": self.total_invocations,
            "performance_level": self.get_performance_level(),
            "memory_usage_level": self.get_memory_usage_level(),
            "performance_score": self.calculate_performance_score(),
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
__all__ = ["ModelAnalyticsPerformanceMetrics"]
