"""
Node Performance Summary Model.

Structured performance summary data for nodes.
Follows ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelNodePerformanceSummary(BaseModel):
    """
    Structured performance summary for nodes.

    Replaces primitive soup unions with typed fields.
    """

    # Usage metrics
    usage_count: int = Field(description="Total usage count")
    success_rate_percentage: float = Field(description="Success rate as percentage")
    error_rate_percentage: float = Field(description="Error rate as percentage")

    # Performance metrics
    average_execution_time_ms: float = Field(
        description="Average execution time in milliseconds"
    )
    average_execution_time_seconds: float = Field(
        description="Average execution time in seconds"
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
        description="Whether node has performance issues"
    )
    is_reliable: bool = Field(description="Whether node is reliable")

    # Improvement suggestions
    improvement_suggestions: list[str] = Field(
        default_factory=list, description="List of performance improvement suggestions"
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
        elif self.is_reliable and self.has_performance_issues:
            return "Good"
        elif not self.is_reliable and not self.has_performance_issues:
            return "Fair"
        else:
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


# Export for use
__all__ = ["ModelNodePerformanceSummary"]
