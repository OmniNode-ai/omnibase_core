"""
Node Performance Metrics Model.

Usage, performance, and execution metrics for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_node_performance_summary import ModelNodePerformanceSummary


class ModelNodePerformanceMetrics(BaseModel):
    """
    Node performance and usage metrics.

    Focused on execution statistics and performance indicators.
    Implements Core protocols:
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Usage metrics
    usage_count: int = Field(default=0, description="Usage count")
    success_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Success rate (0-1)",
    )
    error_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Error rate (0-1)",
    )

    # Performance metrics
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
    )
    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")

    @property
    def has_usage_data(self) -> bool:
        """Check if usage data is available."""
        return self.usage_count > 0

    @property
    def average_execution_time_seconds(self) -> float:
        """Get average execution time in seconds."""
        return self.average_execution_time_ms / 1000.0

    @property
    def is_high_usage(self) -> bool:
        """Check if node has high usage (>100 uses)."""
        return self.usage_count > 100

    @property
    def is_reliable(self) -> bool:
        """Check if node is reliable (success rate > 95%)."""
        return self.success_rate > 0.95

    @property
    def has_performance_issues(self) -> bool:
        """Check if node has performance issues."""
        return (
            self.error_rate > 0.1  # Error rate > 10%
            or self.average_execution_time_ms > 1000.0  # Execution time > 1 second
            or self.memory_usage_mb > 100.0  # Memory usage > 100MB
        )

    def get_success_rate_percentage(self) -> float:
        """Get success rate as percentage."""
        return self.success_rate * 100.0

    def get_error_rate_percentage(self) -> float:
        """Get error rate as percentage."""
        return self.error_rate * 100.0

    def get_performance_level(self) -> str:
        """Get descriptive performance level."""
        if not self.has_usage_data:
            return "No Data"

        if self.average_execution_time_ms <= 100.0:
            return "Fast"
        if self.average_execution_time_ms <= 500.0:
            return "Moderate"
        if self.average_execution_time_ms <= 1000.0:
            return "Slow"
        return "Very Slow"

    def get_reliability_level(self) -> str:
        """Get descriptive reliability level."""
        if not self.has_usage_data:
            return "No Data"

        if self.success_rate >= 0.99:
            return "Excellent"
        if self.success_rate >= 0.95:
            return "Good"
        if self.success_rate >= 0.90:
            return "Fair"
        if self.success_rate >= 0.80:
            return "Poor"
        return "Unreliable"

    def get_memory_usage_level(self) -> str:
        """Get descriptive memory usage level."""
        if self.memory_usage_mb <= 10.0:
            return "Low"
        if self.memory_usage_mb <= 50.0:
            return "Moderate"
        if self.memory_usage_mb <= 100.0:
            return "High"
        return "Very High"

    def calculate_performance_score(self) -> float:
        """Calculate composite performance score (0-100)."""
        if not self.has_usage_data:
            return 0.0

        # Success rate score (40% weight)
        success_score = self.success_rate * 40.0

        # Performance score based on execution time (35% weight)
        if self.average_execution_time_ms <= 100.0:
            perf_score = 35.0
        elif self.average_execution_time_ms <= 250.0:
            perf_score = 25.0
        elif self.average_execution_time_ms <= 500.0:
            perf_score = 15.0
        elif self.average_execution_time_ms <= 1000.0:
            perf_score = 8.0
        else:
            perf_score = 2.0

        # Memory efficiency score (25% weight)
        if self.memory_usage_mb <= 10.0:
            memory_score = 25.0
        elif self.memory_usage_mb <= 25.0:
            memory_score = 20.0
        elif self.memory_usage_mb <= 50.0:
            memory_score = 15.0
        elif self.memory_usage_mb <= 100.0:
            memory_score = 8.0
        else:
            memory_score = 2.0

        return success_score + perf_score + memory_score

    def update_usage_metrics(
        self,
        usage_count: int,
        success_rate: float,
        error_rate: float,
    ) -> None:
        """Update usage metrics."""
        self.usage_count = max(0, usage_count)
        self.success_rate = max(0.0, min(1.0, success_rate))
        self.error_rate = max(0.0, min(1.0, error_rate))

    def update_performance_metrics(
        self,
        avg_execution_time_ms: float,
        memory_usage_mb: float,
    ) -> None:
        """Update performance metrics."""
        self.average_execution_time_ms = max(0.0, avg_execution_time_ms)
        self.memory_usage_mb = max(0.0, memory_usage_mb)

    def add_execution_sample(
        self,
        execution_time_ms: float,
        success: bool,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Add a new execution sample and update metrics."""
        if self.usage_count == 0:
            # First sample
            self.average_execution_time_ms = execution_time_ms
            self.success_rate = 1.0 if success else 0.0
            self.error_rate = 0.0 if success else 1.0
        else:
            # Update running averages
            total_time = self.average_execution_time_ms * self.usage_count
            total_time += execution_time_ms
            self.average_execution_time_ms = total_time / (self.usage_count + 1)

            # Update success/error rates
            total_successes = self.success_rate * self.usage_count
            if success:
                total_successes += 1
            self.success_rate = total_successes / (self.usage_count + 1)
            self.error_rate = 1.0 - self.success_rate

        # Update memory usage (peak)
        self.memory_usage_mb = max(memory_usage_mb, self.memory_usage_mb)

        self.usage_count += 1

    def get_improvement_suggestions(self) -> list[str]:
        """Get performance improvement suggestions."""
        suggestions = []

        if self.success_rate < 0.9:
            suggestions.append("Improve error handling to increase success rate")

        if self.average_execution_time_ms > 500.0:
            suggestions.append("Optimize execution time performance")

        if self.memory_usage_mb > 50.0:
            suggestions.append("Optimize memory usage")

        if self.error_rate > 0.1:
            suggestions.append("Reduce error rate through better validation")

        if not self.has_usage_data:
            suggestions.append("Gather usage metrics to assess performance")

        return suggestions

    def get_performance_summary(self) -> ModelNodePerformanceSummary:
        """Get comprehensive performance summary."""
        return ModelNodePerformanceSummary.create_summary(
            usage_count=self.usage_count,
            success_rate_percentage=self.get_success_rate_percentage(),
            error_rate_percentage=self.get_error_rate_percentage(),
            average_execution_time_ms=self.average_execution_time_ms,
            average_execution_time_seconds=self.average_execution_time_seconds,
            memory_usage_mb=self.memory_usage_mb,
            performance_level=self.get_performance_level(),
            reliability_level=self.get_reliability_level(),
            memory_usage_level=self.get_memory_usage_level(),
            performance_score=self.calculate_performance_score(),
            has_performance_issues=self.has_performance_issues,
            is_reliable=self.is_reliable,
            improvement_suggestions=self.get_improvement_suggestions(),
        )

    @classmethod
    def create_unused(cls) -> ModelNodePerformanceMetrics:
        """Create performance metrics for unused node."""
        return cls()

    @classmethod
    def create_high_performance(cls) -> ModelNodePerformanceMetrics:
        """Create high-performance metrics."""
        return cls(
            usage_count=1000,
            success_rate=0.99,
            error_rate=0.01,
            average_execution_time_ms=50.0,
            memory_usage_mb=15.0,
        )

    @classmethod
    def create_poor_performance(cls) -> ModelNodePerformanceMetrics:
        """Create poor performance metrics."""
        return cls(
            usage_count=50,
            success_rate=0.75,
            error_rate=0.25,
            average_execution_time_ms=1500.0,
            memory_usage_mb=150.0,
        )

    @classmethod
    def create_with_metrics(
        cls,
        usage_count: int,
        success_rate: float,
        error_rate: float,
        avg_execution_time_ms: float,
        memory_usage_mb: float,
    ) -> ModelNodePerformanceMetrics:
        """Create performance metrics with specific values."""
        return cls(
            usage_count=usage_count,
            success_rate=success_rate,
            error_rate=error_rate,
            average_execution_time_ms=avg_execution_time_ms,
            memory_usage_mb=memory_usage_mb,
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
        # Pack performance metrics fields into metadata dict
        result["metadata"] = {
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "average_execution_time_ms": self.average_execution_time_ms,
            "average_execution_time_seconds": self.average_execution_time_seconds,
            "memory_usage_mb": self.memory_usage_mb,
            "has_usage_data": self.has_usage_data,
            "is_reliable": self.is_reliable,
            "has_performance_issues": self.has_performance_issues,
            "performance_level": self.get_performance_level(),
            "reliability_level": self.get_reliability_level(),
            "memory_usage_level": self.get_memory_usage_level(),
            "performance_score": self.calculate_performance_score(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol).

        Raises:
            ModelOnexError: If setting metadata fails with details about the failure
        """
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Setting metadata failed: {e}",
            ) from e

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol).

        Raises:
            ModelOnexError: If validation fails with details about the failure
        """
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Instance validation failed: {e}",
            ) from e


# Export for use
__all__ = ["ModelNodePerformanceMetrics", "ModelNodePerformanceSummary"]
