"""
Node Performance Metrics Model.

Performance and usage statistics for nodes.
Part of the ModelNodeMetadataInfo restructuring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypedDict

from pydantic import BaseModel, Field


class PerformanceSummary(TypedDict):
    """Type-safe performance summary structure."""

    usage_count: int
    error_count: int
    success_rate: float
    has_errors: bool
    is_high_usage: bool


class ModelNodePerformanceMetrics(BaseModel):
    """
    Node performance and usage metrics.

    Contains performance-related data:
    - Usage and error counts
    - Success rate calculations
    - Timestamp tracking
    """

    # Usage metrics (2 fields)
    usage_count: int = Field(default=0, description="Usage count", ge=0)
    error_count: int = Field(default=0, description="Error count", ge=0)

    # Performance indicators (1 field)
    success_rate: float = Field(
        default=100.0,
        description="Success rate percentage",
        ge=0.0,
        le=100.0,
    )

    # Timestamps (3 fields)
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )
    last_accessed: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )

    def has_errors(self) -> bool:
        """Check if node has errors."""
        return self.error_count > 0

    def get_success_rate(self) -> float:
        """Get success rate."""
        return self.success_rate

    def is_high_usage(self) -> bool:
        """Check if node has high usage (>100 uses)."""
        return self.usage_count > 100

    def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1

    def increment_errors(self) -> None:
        """Increment error count and update success rate."""
        self.error_count += 1
        if self.usage_count > 0:
            success_count = self.usage_count - self.error_count
            self.success_rate = (success_count / self.usage_count) * 100.0

    def update_accessed_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(UTC)

    def get_performance_summary(self) -> PerformanceSummary:
        """Get performance metrics summary."""
        return PerformanceSummary(
            usage_count=self.usage_count,
            error_count=self.error_count,
            success_rate=self.success_rate,
            has_errors=self.has_errors(),
            is_high_usage=self.is_high_usage(),
        )

    @classmethod
    def create_new(cls) -> ModelNodePerformanceMetrics:
        """Create new performance metrics with defaults."""
        return cls(
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )


# Export for use
__all__ = ["ModelNodePerformanceMetrics"]
