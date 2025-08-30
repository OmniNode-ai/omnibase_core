"""Performance Monitoring Utility for Intelligence Capture Operations.

This utility provides comprehensive performance monitoring for debug intelligence
capture operations, including timing, memory usage, and effectiveness metrics.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from uuid import UUID, uuid4

import psutil

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for intelligence operations."""

    operation_id: UUID = field(default_factory=uuid4)
    operation_type: str = ""
    agent_name: str = ""
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    duration_ms: float | None = None
    memory_before_mb: float = 0.0
    memory_after_mb: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    entries_processed: int = 0
    errors_encountered: int = 0
    success: bool = False
    context: dict[str, str | int | float | bool] = field(default_factory=dict)

    def calculate_duration(self) -> float:
        """Calculate operation duration in milliseconds."""
        if self.end_time and self.start_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        return self.duration_ms or 0.0

    def calculate_memory_impact(self) -> float:
        """Calculate memory impact in MB."""
        return self.memory_after_mb - self.memory_before_mb

    def is_performance_acceptable(self) -> bool:
        """Check if performance meets acceptable thresholds."""
        # Define acceptable thresholds
        max_duration_ms = 5000  # 5 seconds
        max_memory_mb = 100  # 100 MB
        max_cpu_percent = 80  # 80% CPU

        return (
            (self.duration_ms or 0) <= max_duration_ms
            and self.calculate_memory_impact() <= max_memory_mb
            and self.cpu_usage_percent <= max_cpu_percent
        )


class UtilityIntelligencePerformanceMonitor:
    """Utility for monitoring intelligence capture operation performance."""

    def __init__(self):
        """Initialize performance monitor."""
        self._active_operations: dict[UUID, PerformanceMetrics] = {}
        self._completed_operations: list[PerformanceMetrics] = []
        self._max_history = 1000  # Keep last 1000 operations

        # System monitoring
        self._process = psutil.Process()

    def start_operation(
        self,
        operation_type: str,
        agent_name: str,
        context: dict[str, str | int | float | bool] | None = None,
    ) -> UUID:
        """Start monitoring a new intelligence operation.

        Args:
            operation_type: Type of operation (e.g., 'capture_solution', 'query_similar')
            agent_name: Name of the agent performing the operation
            context: Additional context information

        Returns:
            UUID: Operation ID for tracking
        """
        operation_id = uuid4()

        # Get current system metrics
        memory_info = self._process.memory_info()
        cpu_percent = self._process.cpu_percent()

        metrics = PerformanceMetrics(
            operation_id=operation_id,
            operation_type=operation_type,
            agent_name=agent_name,
            start_time=datetime.utcnow(),
            memory_before_mb=memory_info.rss / (1024 * 1024),
            memory_peak_mb=memory_info.rss / (1024 * 1024),
            cpu_usage_percent=cpu_percent,
            context=context or {},
        )

        self._active_operations[operation_id] = metrics

        logger.debug(
            "Started performance monitoring",
            extra={
                "operation_id": str(operation_id),
                "operation_type": operation_type,
                "agent_name": agent_name,
                "initial_memory_mb": metrics.memory_before_mb,
            },
        )

        return operation_id

    def update_operation(
        self,
        operation_id: UUID,
        entries_processed: int | None = None,
        errors_encountered: int | None = None,
        context_update: dict[str, str | int | float | bool] | None = None,
    ):
        """Update metrics for an ongoing operation.

        Args:
            operation_id: Operation ID to update
            entries_processed: Number of entries processed so far
            errors_encountered: Number of errors encountered
            context_update: Additional context to merge
        """
        if operation_id not in self._active_operations:
            logger.warning(
                "Attempt to update unknown operation",
                extra={"operation_id": str(operation_id)},
            )
            return

        metrics = self._active_operations[operation_id]

        # Update metrics
        if entries_processed is not None:
            metrics.entries_processed = entries_processed
        if errors_encountered is not None:
            metrics.errors_encountered = errors_encountered
        if context_update:
            metrics.context.update(context_update)

        # Update memory peak
        current_memory = self._process.memory_info().rss / (1024 * 1024)
        metrics.memory_peak_mb = max(metrics.memory_peak_mb, current_memory)

    def complete_operation(
        self,
        operation_id: UUID,
        success: bool = True,
    ) -> PerformanceMetrics:
        """Complete monitoring for an operation.

        Args:
            operation_id: Operation ID to complete
            success: Whether the operation completed successfully

        Returns:
            Completed performance metrics

        Raises:
            OnexError: If operation ID not found
        """
        if operation_id not in self._active_operations:
            raise OnexError(
                error_code=CoreErrorCode.OPERATION_FAILED,
                message=f"Unknown operation ID: {operation_id}",
                context={"operation_id": str(operation_id)},
            )

        metrics = self._active_operations.pop(operation_id)

        # Finalize metrics
        metrics.end_time = datetime.utcnow()
        metrics.duration_ms = metrics.calculate_duration()
        metrics.success = success
        metrics.memory_after_mb = self._process.memory_info().rss / (1024 * 1024)

        # Add to completed operations
        self._completed_operations.append(metrics)

        # Maintain history limit
        if len(self._completed_operations) > self._max_history:
            self._completed_operations = self._completed_operations[
                -self._max_history :
            ]

        # Log performance summary
        memory_impact = metrics.calculate_memory_impact()
        performance_acceptable = metrics.is_performance_acceptable()

        log_level = logging.INFO if performance_acceptable else logging.WARNING
        logger.log(
            log_level,
            "Operation completed",
            extra={
                "operation_id": str(operation_id),
                "operation_type": metrics.operation_type,
                "agent_name": metrics.agent_name,
                "duration_ms": metrics.duration_ms,
                "memory_impact_mb": memory_impact,
                "entries_processed": metrics.entries_processed,
                "errors_encountered": metrics.errors_encountered,
                "success": success,
                "performance_acceptable": performance_acceptable,
            },
        )

        return metrics

    def get_operation_statistics(
        self,
        agent_name: str | None = None,
        operation_type: str | None = None,
        time_window_hours: int | None = None,
    ) -> dict[str, int | float | list[str]]:
        """Get performance statistics for operations.

        Args:
            agent_name: Filter by specific agent name
            operation_type: Filter by specific operation type
            time_window_hours: Only include operations within this time window

        Returns:
            Dictionary with performance statistics
        """
        # Filter operations
        filtered_ops = self._completed_operations

        if agent_name:
            filtered_ops = [op for op in filtered_ops if op.agent_name == agent_name]

        if operation_type:
            filtered_ops = [
                op for op in filtered_ops if op.operation_type == operation_type
            ]

        if time_window_hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            filtered_ops = [op for op in filtered_ops if op.start_time >= cutoff_time]

        if not filtered_ops:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "average_duration_ms": 0.0,
                "average_memory_impact_mb": 0.0,
                "performance_acceptable_rate": 0.0,
            }

        # Calculate statistics
        total_ops = len(filtered_ops)
        successful_ops = len([op for op in filtered_ops if op.success])

        durations = [op.duration_ms for op in filtered_ops if op.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        memory_impacts = [op.calculate_memory_impact() for op in filtered_ops]
        avg_memory_impact = (
            sum(memory_impacts) / len(memory_impacts) if memory_impacts else 0.0
        )

        acceptable_ops = len(
            [op for op in filtered_ops if op.is_performance_acceptable()],
        )
        acceptable_rate = acceptable_ops / total_ops if total_ops > 0 else 0.0

        # Get top operation types
        op_type_counts = {}
        for op in filtered_ops:
            op_type_counts[op.operation_type] = (
                op_type_counts.get(op.operation_type, 0) + 1
            )

        top_operation_types = sorted(
            op_type_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:5]

        return {
            "total_operations": total_ops,
            "success_rate": successful_ops / total_ops if total_ops > 0 else 0.0,
            "average_duration_ms": round(avg_duration, 2),
            "average_memory_impact_mb": round(avg_memory_impact, 2),
            "performance_acceptable_rate": round(acceptable_rate, 2),
            "slowest_operation_ms": max(durations) if durations else 0.0,
            "fastest_operation_ms": min(durations) if durations else 0.0,
            "total_entries_processed": sum(op.entries_processed for op in filtered_ops),
            "total_errors": sum(op.errors_encountered for op in filtered_ops),
            "top_operation_types": [
                f"{op_type}: {count}" for op_type, count in top_operation_types
            ],
            "active_operations_count": len(self._active_operations),
        }

    def get_agent_performance_report(
        self,
        agent_name: str,
    ) -> dict[str, int | float | list[str]]:
        """Get comprehensive performance report for a specific agent.

        Args:
            agent_name: Name of the agent to analyze

        Returns:
            Detailed performance report
        """
        agent_ops = [
            op for op in self._completed_operations if op.agent_name == agent_name
        ]

        if not agent_ops:
            return {"error": f"No operations found for agent: {agent_name}"}

        # Get recent performance (last 24 hours)
        recent_stats = self.get_operation_statistics(
            agent_name=agent_name,
            time_window_hours=24,
        )

        # Get overall performance
        overall_stats = self.get_operation_statistics(agent_name=agent_name)

        # Performance trends
        recent_ops = [
            op
            for op in agent_ops
            if op.start_time >= datetime.utcnow() - timedelta(hours=24)
        ]
        older_ops = [
            op
            for op in agent_ops
            if op.start_time < datetime.utcnow() - timedelta(hours=24)
        ]

        performance_trend = "stable"
        if recent_ops and older_ops:
            recent_avg_duration = sum(op.duration_ms or 0 for op in recent_ops) / len(
                recent_ops,
            )
            older_avg_duration = sum(op.duration_ms or 0 for op in older_ops) / len(
                older_ops,
            )

            if recent_avg_duration > older_avg_duration * 1.2:
                performance_trend = "degrading"
            elif recent_avg_duration < older_avg_duration * 0.8:
                performance_trend = "improving"

        return {
            "agent_name": agent_name,
            "recent_24h": recent_stats,
            "overall": overall_stats,
            "performance_trend": performance_trend,
            "first_operation": min(op.start_time for op in agent_ops).isoformat(),
            "last_operation": max(op.start_time for op in agent_ops).isoformat(),
            "problem_solving_efficiency": self._calculate_efficiency_score(agent_ops),
        }

    def _calculate_efficiency_score(
        self,
        operations: list[PerformanceMetrics],
    ) -> float:
        """Calculate an efficiency score based on multiple performance factors."""
        if not operations:
            return 0.0

        # Factors: success rate, speed, memory efficiency, error rate
        success_rate = len([op for op in operations if op.success]) / len(operations)

        durations = [op.duration_ms for op in operations if op.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        speed_score = max(0, 1 - (avg_duration / 10000))  # Penalty for operations > 10s

        memory_impacts = [abs(op.calculate_memory_impact()) for op in operations]
        avg_memory = (
            sum(memory_impacts) / len(memory_impacts) if memory_impacts else 0.0
        )
        memory_score = max(0, 1 - (avg_memory / 100))  # Penalty for > 100MB impact

        total_errors = sum(op.errors_encountered for op in operations)
        error_rate = total_errors / len(operations)
        error_score = max(0, 1 - error_rate)

        # Weighted efficiency score
        efficiency = (
            success_rate * 0.4  # Success is most important
            + speed_score * 0.3  # Speed matters
            + memory_score * 0.2  # Memory efficiency
            + error_score * 0.1  # Low error rate
        )

        return round(efficiency, 3)

    def clear_history(self):
        """Clear operation history (keep active operations)."""
        self._completed_operations.clear()
        logger.info("Performance monitor history cleared")


def monitor_intelligence_operation(operation_type: str):
    """Decorator to automatically monitor intelligence operations.

    Args:
        operation_type: Type of operation being monitored

    Usage:
        @monitor_intelligence_operation("capture_solution")
        def capture_solution(self, ...):
            # Operation logic here
            return result
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Check if the instance has a performance monitor
            monitor_attr = getattr(self, "performance_monitor", None)
            if not monitor_attr:
                # No monitor available, execute normally
                return func(self, *args, **kwargs)

            agent_name = getattr(self, "agent_name", "unknown_agent")

            # Start monitoring
            operation_id = monitor_attr.start_operation(
                operation_type=operation_type,
                agent_name=agent_name,
                context={"function": func.__name__, "args_count": len(args)},
            )

            try:
                # Execute the function
                result = func(self, *args, **kwargs)

                # Complete monitoring successfully
                monitor_attr.complete_operation(operation_id, success=True)
                return result

            except Exception as e:
                # Complete monitoring with failure
                monitor_attr.complete_operation(operation_id, success=False)
                monitor_attr.update_operation(
                    operation_id,
                    errors_encountered=1,
                    context_update={"error": str(e)},
                )
                raise

        return wrapper

    return decorator


# Global instance for easy access
performance_monitor = UtilityIntelligencePerformanceMonitor()


def get_intelligence_performance_stats(
    agent_name: str | None = None,
) -> dict[str, int | float | list[str]]:
    """Convenience function to get intelligence performance statistics.

    Args:
        agent_name: Optional agent name filter

    Returns:
        Performance statistics dictionary
    """
    return performance_monitor.get_operation_statistics(agent_name=agent_name)


def get_agent_performance_report(
    agent_name: str,
) -> dict[str, int | float | list[str]]:
    """Convenience function to get agent performance report.

    Args:
        agent_name: Name of the agent

    Returns:
        Comprehensive agent performance report
    """
    return performance_monitor.get_agent_performance_report(agent_name)
