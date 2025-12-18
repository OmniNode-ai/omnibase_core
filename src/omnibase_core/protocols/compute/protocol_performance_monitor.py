"""
ProtocolPerformanceMonitor - Protocol for performance monitoring implementations.

This protocol defines the interface for performance monitoring implementations,
enabling duck typing across different implementations without requiring direct
inheritance.

Design:
    This protocol uses dependency inversion - Core defines the interface,
    and implementations (PerformanceMonitor in omnibase_core.monitoring or custom)
    satisfy the contract. This enables consistent performance monitoring behavior
    across the ONEX ecosystem while allowing implementation flexibility.

Thread Safety:
    WARNING: Thread safety is implementation-specific. Callers should verify
    the thread safety guarantees of their chosen implementation.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.compute import ProtocolPerformanceMonitor

        def track_service_resolution(
            monitor: ProtocolPerformanceMonitor,
            operation_name: str,
            duration_ms: float,
            cache_hit: bool,
            correlation_id: str,
        ) -> None:
            '''Track a service resolution operation.'''
            monitor.track_operation(
                operation_name=operation_name,
                duration_ms=duration_ms,
                cache_hit=cache_hit,
                correlation_id=correlation_id,
            )

Related:
    - TypedDictPerformanceCheckpointResult: Return type for run_optimization_checkpoint
    - ModelONEXContainer: Primary consumer of PerformanceMonitor implementations

.. versionadded:: 0.4.0
"""

from __future__ import annotations

__all__ = [
    "ProtocolPerformanceMonitor",
]

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnibase_core.types.typed_dict_monitoring_dashboard import (
        TypedDictMonitoringDashboard,
    )
    from omnibase_core.types.typed_dict_performance_checkpoint_result import (
        TypedDictPerformanceCheckpointResult,
    )


@runtime_checkable
class ProtocolPerformanceMonitor(Protocol):
    """
    Protocol for performance monitoring implementations.

    Defines the interface for performance monitoring used by ModelONEXContainer
    to track operation metrics, cache performance, and generate optimization
    recommendations.

    Required Methods:
        - track_operation: Record metrics for an operation
        - get_monitoring_dashboard: Get current monitoring statistics
        - run_optimization_checkpoint: Run async checkpoint analysis

    Thread Safety:
        WARNING: Implementations are NOT guaranteed to be thread-safe.
        See implementation-specific documentation for thread safety guarantees.

    Example:
        .. code-block:: python

            from omnibase_core.protocols.compute import ProtocolPerformanceMonitor
            from omnibase_core.types import (
                TypedDictMonitoringDashboard,
                TypedDictPerformanceCheckpointResult,
            )

            class SimplePerformanceMonitor:
                '''Minimal performance monitor implementation.'''

                def __init__(self) -> None:
                    self._operations: list[dict[str, str | float | bool]] = []

                def track_operation(
                    self,
                    operation_name: str,
                    duration_ms: float,
                    cache_hit: bool,
                    correlation_id: str,
                ) -> None:
                    self._operations.append({
                        "name": operation_name,
                        "duration_ms": duration_ms,
                        "cache_hit": cache_hit,
                        "correlation_id": correlation_id,
                    })

                def get_monitoring_dashboard(self) -> TypedDictMonitoringDashboard:
                    return {
                        "total_operations": len(self._operations),
                        "avg_duration_ms": sum(float(op["duration_ms"]) for op in self._operations) / len(self._operations) if self._operations else 0.0,
                    }

                async def run_optimization_checkpoint(
                    self, phase_name: str
                ) -> TypedDictPerformanceCheckpointResult:
                    # TypedDict is not callable - use dict literal syntax
                    return {
                        "phase": phase_name,
                        "status": "ok",
                        "metrics": {"operations_tracked": len(self._operations)},
                        "recommendations": [],
                    }

            # Verify protocol conformance
            monitor: ProtocolPerformanceMonitor = SimplePerformanceMonitor()
            assert isinstance(monitor, ProtocolPerformanceMonitor)

    .. versionadded:: 0.4.0
    """

    def track_operation(
        self,
        operation_name: str,
        duration_ms: float,
        cache_hit: bool,
        correlation_id: str,
    ) -> None:
        """
        Record metrics for an operation.

        This method should be called after each monitored operation to:
        - Track operation duration for performance analysis
        - Record cache hit/miss statistics
        - Associate metrics with correlation IDs for distributed tracing

        Args:
            operation_name: Name of the operation being tracked (e.g., "service_resolution_MyService")
            duration_ms: Duration of the operation in milliseconds
            cache_hit: Whether the operation benefited from cached data
            correlation_id: Unique identifier for correlating related operations

        Note:
            Implementations should handle high-frequency calls efficiently.
            Consider using buffering or sampling for high-volume scenarios.
        """
        ...

    def get_monitoring_dashboard(self) -> TypedDictMonitoringDashboard:
        """
        Get current monitoring statistics for dashboard display.

        Returns:
            Dictionary containing monitoring statistics. The exact structure
            is implementation-defined but typically includes:
            - total_operations: Total number of tracked operations
            - avg_duration_ms: Average operation duration
            - cache_hit_rate: Percentage of operations with cache hits
            - operations_by_type: Breakdown by operation_name

        Note:
            This method is synchronous for efficient dashboard polling.
            Heavy computations should be pre-computed or cached.
        """
        ...

    async def run_optimization_checkpoint(
        self, phase_name: str
    ) -> TypedDictPerformanceCheckpointResult:
        """
        Run a comprehensive performance checkpoint analysis.

        This async method analyzes collected metrics and generates
        optimization recommendations for the specified phase.

        Args:
            phase_name: Name of the checkpoint phase (e.g., "production", "development")

        Returns:
            TypedDictPerformanceCheckpointResult containing:
            - phase: The phase name
            - timestamp: When the checkpoint was run
            - metrics: Performance metrics data
            - recommendations: List of optimization suggestions
            - status: Checkpoint status ("ok", "warning", "critical")
            - error: Optional error message if checkpoint failed

        Note:
            This is async to allow for potentially expensive analysis
            operations without blocking the event loop.
        """
        ...
