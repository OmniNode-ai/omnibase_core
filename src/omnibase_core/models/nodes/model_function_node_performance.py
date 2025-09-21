"""
Function Node Performance Model.

Performance metrics and complexity information for function nodes.
Part of the ModelFunctionNode restructuring to reduce excessive string fields.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ...enums.enum_complexity import EnumComplexity
from ...enums.enum_memory_usage import EnumMemoryUsage
from ...enums.enum_runtime_category import EnumRuntimeCategory


class ModelFunctionNodePerformance(BaseModel):
    """
    Function node performance and complexity information.

    Contains performance metrics, complexity analysis, and runtime characteristics
    without core function or documentation concerns.
    """

    # Performance and usage
    complexity: EnumComplexity = Field(
        default=EnumComplexity.SIMPLE,
        description="Function complexity (simple, moderate, complex)",
    )
    estimated_runtime: EnumRuntimeCategory | None = Field(
        default=None,
        description="Estimated runtime category",
    )
    memory_usage: EnumMemoryUsage | None = Field(
        default=None,
        description="Memory usage category",
    )

    # Code quality metrics
    cyclomatic_complexity: int = Field(
        default=1,
        description="Cyclomatic complexity score",
        ge=1,
    )
    lines_of_code: int = Field(
        default=0,
        description="Lines of code",
        ge=0,
    )

    # Runtime metrics
    execution_count: int = Field(
        default=0,
        description="Number of executions",
        ge=0,
    )
    success_rate: float = Field(
        default=0.0,
        description="Success rate (0-1)",
        ge=0.0,
        le=1.0,
    )
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
    memory_usage_mb: float = Field(
        default=0.0,
        description="Memory usage in MB",
        ge=0.0,
    )

    def get_complexity_level(self) -> int:
        """Get numeric complexity level."""
        complexity_map = {
            EnumComplexity.SIMPLE: 1,
            EnumComplexity.MODERATE: 2,
            EnumComplexity.COMPLEX: 3,
            EnumComplexity.VERY_COMPLEX: 4,
        }
        return complexity_map.get(self.complexity, 1)

    def is_high_performance(self) -> bool:
        """Check if function has good performance characteristics."""
        return (
            self.average_execution_time_ms < 100.0
            and self.memory_usage_mb < 10.0
            and self.success_rate > 0.95
        )

    def is_complex_function(self) -> bool:
        """Check if function is complex."""
        return (
            self.complexity in {EnumComplexity.COMPLEX, EnumComplexity.VERY_COMPLEX}
            or self.cyclomatic_complexity > 10
            or self.lines_of_code > 100
        )

    def get_performance_score(self) -> float:
        """Calculate overall performance score (0-1)."""
        score = 0.0

        # Success rate component (40%)
        score += self.success_rate * 0.4

        # Execution time component (30%)
        if self.average_execution_time_ms < 10:
            score += 0.3
        elif self.average_execution_time_ms < 100:
            score += 0.2
        elif self.average_execution_time_ms < 1000:
            score += 0.1

        # Memory usage component (20%)
        if self.memory_usage_mb < 1:
            score += 0.2
        elif self.memory_usage_mb < 10:
            score += 0.1

        # Complexity component (10%)
        if self.complexity == EnumComplexity.SIMPLE:
            score += 0.1
        elif self.complexity == EnumComplexity.MODERATE:
            score += 0.05

        return min(score, 1.0)

    def record_execution(
        self,
        success: bool,
        execution_time_ms: float,
        memory_used_mb: float = 0.0,
    ) -> None:
        """Record a function execution."""
        self.execution_count += 1

        # Update success rate
        if self.execution_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            current_successes = (self.execution_count - 1) * self.success_rate
            if success:
                current_successes += 1
            self.success_rate = current_successes / self.execution_count

        # Update average execution time
        if self.execution_count == 1:
            self.average_execution_time_ms = execution_time_ms
        else:
            total_time = (self.execution_count - 1) * self.average_execution_time_ms
            total_time += execution_time_ms
            self.average_execution_time_ms = total_time / self.execution_count

        # Update memory usage
        if memory_used_mb > 0:
            if self.execution_count == 1:
                self.memory_usage_mb = memory_used_mb
            else:
                total_memory = (self.execution_count - 1) * self.memory_usage_mb
                total_memory += memory_used_mb
                self.memory_usage_mb = total_memory / self.execution_count

    def reset_metrics(self) -> None:
        """Reset all runtime metrics."""
        self.execution_count = 0
        self.success_rate = 0.0
        self.average_execution_time_ms = 0.0
        self.memory_usage_mb = 0.0

    @classmethod
    def create_simple(cls) -> ModelFunctionNodePerformance:
        """Create simple performance profile."""
        return cls(complexity=EnumComplexity.SIMPLE)

    @classmethod
    def create_complex(
        cls,
        cyclomatic_complexity: int = 15,
        lines_of_code: int = 200,
    ) -> ModelFunctionNodePerformance:
        """Create complex performance profile."""
        return cls(
            complexity=EnumComplexity.COMPLEX,
            cyclomatic_complexity=cyclomatic_complexity,
            lines_of_code=lines_of_code,
        )

    @classmethod
    def create_high_performance(cls) -> ModelFunctionNodePerformance:
        """Create high-performance profile."""
        return cls(
            complexity=EnumComplexity.SIMPLE,
            estimated_runtime=EnumRuntimeCategory.FAST,
            memory_usage=EnumMemoryUsage.LOW,
            success_rate=0.99,
            average_execution_time_ms=5.0,
            memory_usage_mb=0.5,
        )


# Export for use
__all__ = ["ModelFunctionNodePerformance"]
