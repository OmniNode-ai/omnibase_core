"""
TypedDict for performance checkpoint results.

Used by ModelONEXContainer.run_performance_checkpoint() method.
"""

from typing import NotRequired, TypedDict


class TypedDictPerformanceCheckpointResult(TypedDict, total=True):
    """
    TypedDict for performance checkpoint result.

    Used for ModelONEXContainer.run_performance_checkpoint() return type.

    When performance monitoring is disabled, returns {"error": "..."}.
    When enabled, returns the result from performance_monitor.run_optimization_checkpoint().

    Attributes:
        error: Error message when performance monitoring is not enabled
        phase: The checkpoint phase name
        timestamp: When the checkpoint was run
        metrics: Performance metrics data
        recommendations: Optimization recommendations
        status: Checkpoint status
    """

    error: NotRequired[str]
    phase: NotRequired[str]
    timestamp: NotRequired[str]
    metrics: NotRequired[dict[str, object]]
    recommendations: NotRequired[list[str]]
    status: NotRequired[str]


__all__ = ["TypedDictPerformanceCheckpointResult"]
