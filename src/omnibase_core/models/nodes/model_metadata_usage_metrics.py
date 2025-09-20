"""
Metadata Usage Metrics Model.

Model for tracking usage and performance metrics for metadata nodes.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ModelMetadataUsageMetrics(BaseModel):
    """Usage metrics for metadata nodes."""

    total_invocations: int = Field(
        default=0,
        description="Total number of invocations",
        ge=0,
    )
    success_count: int = Field(
        default=0,
        description="Number of successful invocations",
        ge=0,
    )
    failure_count: int = Field(
        default=0,
        description="Number of failed invocations",
        ge=0,
    )
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
    last_invocation: datetime | None = Field(
        default=None,
        description="Last invocation timestamp",
    )
    peak_memory_usage_mb: float = Field(
        default=0.0,
        description="Peak memory usage in MB",
        ge=0.0,
    )

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_invocations == 0:
            return 100.0
        return (self.success_count / self.total_invocations) * 100.0

    def get_failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.failure_count / self.total_invocations) * 100.0

    def record_invocation(
        self,
        success: bool,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record a new invocation."""
        self.total_invocations += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update averages
        if execution_time_ms > 0:
            current_total = self.average_execution_time_ms * (
                self.total_invocations - 1
            )
            self.average_execution_time_ms = (
                current_total + execution_time_ms
            ) / self.total_invocations

        # Update peak memory usage
        self.peak_memory_usage_mb = max(memory_usage_mb, self.peak_memory_usage_mb)

        self.last_invocation = datetime.now(UTC)


# Export for use
__all__ = ["ModelMetadataUsageMetrics"]