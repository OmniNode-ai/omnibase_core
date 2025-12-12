"""
ONEX Performance Metrics Model.

Performance metrics for ONEX replies including timing and resource usage data.
"""

from pydantic import BaseModel, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelOnexPerformanceMetrics(BaseModel):
    """Performance metrics for Onex replies."""

    processing_time_ms: float = Field(description="Processing time in milliseconds")
    queue_time_ms: float | None = Field(
        default=None,
        description="Queue time in milliseconds",
    )
    network_time_ms: float | None = Field(
        default=None,
        description="Network time in milliseconds",
    )
    memory_usage_mb: float | None = Field(
        default=None,
        description="Memory usage in MB",
    )
    cpu_usage_percent: float | None = Field(
        default=None,
        description="CPU usage percentage",
    )

    @field_validator("processing_time_ms")
    @classmethod
    def validate_processing_time(cls, v: float) -> float:
        """Validate processing time is non-negative."""
        if v < 0:
            msg = "Processing time cannot be negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("queue_time_ms")
    @classmethod
    def validate_queue_time(cls, v: float | None) -> float | None:
        """Validate queue time is non-negative if specified."""
        if v is not None and v < 0:
            msg = "Queue time cannot be negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("network_time_ms")
    @classmethod
    def validate_network_time(cls, v: float | None) -> float | None:
        """Validate network time is non-negative if specified."""
        if v is not None and v < 0:
            msg = "Network time cannot be negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("memory_usage_mb")
    @classmethod
    def validate_memory_usage(cls, v: float | None) -> float | None:
        """Validate memory usage is non-negative if specified."""
        if v is not None and v < 0:
            msg = "Memory usage cannot be negative"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    @field_validator("cpu_usage_percent")
    @classmethod
    def validate_cpu_usage(cls, v: float | None) -> float | None:
        """Validate CPU usage is between 0 and 100 if specified."""
        if v is not None and (v < 0 or v > 100):
            msg = "CPU usage must be between 0 and 100"
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=msg,
            )
        return v

    def get_total_time_ms(self) -> float:
        """Get total time including processing, queue, and network time."""
        total = self.processing_time_ms
        if self.queue_time_ms is not None:
            total += self.queue_time_ms
        if self.network_time_ms is not None:
            total += self.network_time_ms
        return total

    def get_efficiency_score(self) -> float | None:
        """
        Calculate efficiency score based on processing time vs total time.
        Returns score between 0 and 1, where 1 is perfectly efficient.
        """
        total_time = self.get_total_time_ms()
        if total_time <= 0:
            return None

        # Pure processing efficiency
        efficiency = self.processing_time_ms / total_time
        return max(0.0, min(1.0, efficiency))

    def is_within_threshold(
        self,
        max_processing_time_ms: float,
        max_memory_mb: float | None = None,
        max_cpu_percent: float | None = None,
    ) -> bool:
        """Check if metrics are within specified thresholds."""
        if self.processing_time_ms > max_processing_time_ms:
            return False

        if max_memory_mb is not None and self.memory_usage_mb is not None:
            if self.memory_usage_mb > max_memory_mb:
                return False

        if max_cpu_percent is not None and self.cpu_usage_percent is not None:
            if self.cpu_usage_percent > max_cpu_percent:
                return False

        return True

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def create_empty(cls) -> "ModelOnexPerformanceMetrics":
        """Create empty performance metrics with zero processing time."""
        return cls(processing_time_ms=0.0)

    @classmethod
    def create_from_timings(
        cls,
        processing_time_ms: float,
        queue_time_ms: float | None = None,
        network_time_ms: float | None = None,
    ) -> "ModelOnexPerformanceMetrics":
        """Create performance metrics from timing data."""
        return cls(
            processing_time_ms=processing_time_ms,
            queue_time_ms=queue_time_ms,
            network_time_ms=network_time_ms,
        )
