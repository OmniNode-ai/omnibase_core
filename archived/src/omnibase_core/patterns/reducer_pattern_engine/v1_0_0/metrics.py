"""
ReducerMetricsCollector - Basic metrics collection for reducer processing.

Provides performance monitoring, success/failure tracking, and memory usage
collection for reducer pattern engine operations.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event


@dataclass
class ModelWorkflowError:
    """Strongly typed workflow error information."""

    error_type: str = ""
    has_error: bool = False
    error_message: str = ""


@dataclass
class ModelWorkflowTiming:
    """Strongly typed workflow timing information."""

    started_at: float = field(default_factory=time.time)
    completed_at: float = 0.0
    is_completed: bool = False


@dataclass
class WorkflowMetrics:
    """Metrics for individual workflow processing."""

    workflow_id: UUID
    workflow_type: str
    processing_time_ms: float
    memory_usage_mb: float
    success: bool
    error_info: ModelWorkflowError = field(default_factory=ModelWorkflowError)
    timing: ModelWorkflowTiming = field(default_factory=ModelWorkflowTiming)


@dataclass
class AggregateMetrics:
    """Aggregate metrics for a workflow type."""

    workflow_type: str
    total_processed: int = 0
    successful_count: int = 0
    failed_count: int = 0
    total_processing_time_ms: float = 0.0
    total_memory_usage_mb: float = 0.0
    min_processing_time_ms: float = float("inf")
    max_processing_time_ms: float = 0.0
    recent_processing_times: deque = field(default_factory=lambda: deque(maxlen=100))

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_processed == 0:
            return 0.0
        return (self.successful_count / self.total_processed) * 100.0

    @property
    def average_processing_time_ms(self) -> float:
        """Calculate average processing time."""
        if self.total_processed == 0:
            return 0.0
        return self.total_processing_time_ms / self.total_processed

    @property
    def average_memory_usage_mb(self) -> float:
        """Calculate average memory usage."""
        if self.total_processed == 0:
            return 0.0
        return self.total_memory_usage_mb / self.total_processed

    @property
    def recent_average_processing_time_ms(self) -> float:
        """Calculate recent average processing time (last 100 workflows)."""
        if not self.recent_processing_times:
            return 0.0
        return sum(self.recent_processing_times) / len(self.recent_processing_times)


class ReducerMetricsCollector:
    """Basic metrics collection for reducer processing."""

    def __init__(self, max_workflow_history: int = 1000):
        """
        Initialize metrics collector.

        Args:
            max_workflow_history: Maximum number of individual workflow metrics to keep
        """
        self._workflow_metrics: deque = deque(maxlen=max_workflow_history)
        self._aggregate_metrics: dict[str, AggregateMetrics] = defaultdict(
            lambda: AggregateMetrics(workflow_type="unknown"),
        )
        self._system_metrics: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._start_time = time.time()

        # Initialize system metrics
        self._update_system_metrics()

    def record_workflow_start(self, workflow_id: UUID, workflow_type: str) -> None:
        """
        Record the start of workflow processing.

        Args:
            workflow_id: Unique workflow identifier
            workflow_type: Type of workflow being processed
        """
        with self._lock:
            # Record initial system state
            current_memory = self._get_memory_usage_mb()

            # This will be updated when workflow completes
            workflow_metrics = WorkflowMetrics(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                processing_time_ms=0.0,
                memory_usage_mb=current_memory,
                success=False,
            )

            emit_log_event(
                level=LogLevel.DEBUG,
                message=f"Started tracking workflow {workflow_id} of type {workflow_type}",
            )

    def record_workflow_completion(
        self,
        workflow_id: UUID,
        workflow_type: str,
        success: bool,
        processing_time_ms: float,
        error_type: str = "",
    ) -> None:
        """
        Record workflow processing completion.

        Args:
            workflow_id: Unique workflow identifier
            workflow_type: Type of workflow processed
            success: Whether processing was successful
            processing_time_ms: Time taken to process workflow
            error_type: Type of error if processing failed
        """
        with self._lock:
            current_memory = self._get_memory_usage_mb()

            # Create error info
            error_info = ModelWorkflowError(
                error_type=error_type,
                has_error=bool(error_type),
                error_message=error_type if error_type else "",
            )

            # Create timing info
            timing = ModelWorkflowTiming(completed_at=time.time(), is_completed=True)

            # Create workflow metrics record
            workflow_metrics = WorkflowMetrics(
                workflow_id=workflow_id,
                workflow_type=workflow_type,
                processing_time_ms=processing_time_ms,
                memory_usage_mb=current_memory,
                success=success,
                error_info=error_info,
                timing=timing,
            )

            # Store individual metrics
            self._workflow_metrics.append(workflow_metrics)

            # Update aggregate metrics
            self._update_aggregate_metrics(workflow_metrics)

            emit_log_event(
                level=LogLevel.DEBUG,
                message=f"Recorded completion for workflow {workflow_id}: "
                f"success={success}, time={processing_time_ms:.2f}ms",
            )

    def record_processing_time(self, workflow_type: str, duration_ms: float) -> None:
        """
        Record processing time for a workflow type.

        Args:
            workflow_type: Type of workflow
            duration_ms: Processing duration in milliseconds
        """
        with self._lock:
            aggregate = self._aggregate_metrics[workflow_type]
            aggregate.workflow_type = workflow_type
            aggregate.total_processing_time_ms += duration_ms
            aggregate.min_processing_time_ms = min(
                aggregate.min_processing_time_ms,
                duration_ms,
            )
            aggregate.max_processing_time_ms = max(
                aggregate.max_processing_time_ms,
                duration_ms,
            )
            aggregate.recent_processing_times.append(duration_ms)

    def increment_success_count(self, workflow_type: str) -> None:
        """
        Increment success counter for a workflow type.

        Args:
            workflow_type: Type of workflow
        """
        with self._lock:
            aggregate = self._aggregate_metrics[workflow_type]
            aggregate.workflow_type = workflow_type
            aggregate.successful_count += 1
            aggregate.total_processed += 1

    def increment_error_count(self, workflow_type: str, error_type: str) -> None:
        """
        Increment error counter for a workflow type.

        Args:
            workflow_type: Type of workflow
            error_type: Type of error that occurred
        """
        with self._lock:
            aggregate = self._aggregate_metrics[workflow_type]
            aggregate.workflow_type = workflow_type
            aggregate.failed_count += 1
            aggregate.total_processed += 1

            # Track error types separately
            error_key = f"{workflow_type}_errors"
            if error_key not in self._system_metrics:
                self._system_metrics[error_key] = defaultdict(int)
            self._system_metrics[error_key][error_type] += 1

    def track_memory_usage(self, workflow_type: str, memory_mb: float) -> None:
        """
        Track memory usage for a workflow type.

        Args:
            workflow_type: Type of workflow
            memory_mb: Memory usage in megabytes
        """
        with self._lock:
            aggregate = self._aggregate_metrics[workflow_type]
            aggregate.workflow_type = workflow_type
            aggregate.total_memory_usage_mb += memory_mb

    def get_metrics_summary(self) -> dict[str, Any]:
        """
        Get comprehensive metrics summary.

        Returns:
            Dictionary containing all collected metrics
        """
        with self._lock:
            self._update_system_metrics()

            summary: dict[str, Any] = {
                "system_metrics": self._system_metrics.copy(),
                "aggregate_metrics": {},
                "workflow_types": list(self._aggregate_metrics.keys()),
                "total_workflows_processed": sum(
                    agg.total_processed for agg in self._aggregate_metrics.values()
                ),
                "overall_success_rate": self._calculate_overall_success_rate(),
                "uptime_seconds": time.time() - self._start_time,
                "collection_timestamp": time.time(),
            }

            # Add aggregate metrics for each workflow type
            for workflow_type, aggregate in self._aggregate_metrics.items():
                summary["aggregate_metrics"][workflow_type] = {
                    "total_processed": aggregate.total_processed,
                    "successful_count": aggregate.successful_count,
                    "failed_count": aggregate.failed_count,
                    "success_rate_percent": aggregate.success_rate,
                    "average_processing_time_ms": aggregate.average_processing_time_ms,
                    "recent_average_processing_time_ms": aggregate.recent_average_processing_time_ms,
                    "min_processing_time_ms": (
                        aggregate.min_processing_time_ms
                        if aggregate.min_processing_time_ms != float("inf")
                        else 0.0
                    ),
                    "max_processing_time_ms": aggregate.max_processing_time_ms,
                    "average_memory_usage_mb": aggregate.average_memory_usage_mb,
                    "total_memory_usage_mb": aggregate.total_memory_usage_mb,
                }

            return summary

    def get_workflow_type_metrics(self, workflow_type: str) -> dict[str, Any]:
        """
        Get metrics for a specific workflow type.

        Args:
            workflow_type: Type of workflow to get metrics for

        Returns:
            Metrics dictionary for the workflow type (empty if not found)
        """
        with self._lock:
            if workflow_type not in self._aggregate_metrics:
                return {
                    "workflow_type": workflow_type,
                    "total_processed": 0,
                    "successful_count": 0,
                    "failed_count": 0,
                    "success_rate_percent": 0.0,
                    "average_processing_time_ms": 0.0,
                    "recent_average_processing_time_ms": 0.0,
                    "min_processing_time_ms": 0.0,
                    "max_processing_time_ms": 0.0,
                    "average_memory_usage_mb": 0.0,
                    "recent_processing_times": [],
                }

            aggregate = self._aggregate_metrics[workflow_type]
            return {
                "workflow_type": workflow_type,
                "total_processed": aggregate.total_processed,
                "successful_count": aggregate.successful_count,
                "failed_count": aggregate.failed_count,
                "success_rate_percent": aggregate.success_rate,
                "average_processing_time_ms": aggregate.average_processing_time_ms,
                "recent_average_processing_time_ms": aggregate.recent_average_processing_time_ms,
                "min_processing_time_ms": (
                    aggregate.min_processing_time_ms
                    if aggregate.min_processing_time_ms != float("inf")
                    else 0.0
                ),
                "max_processing_time_ms": aggregate.max_processing_time_ms,
                "average_memory_usage_mb": aggregate.average_memory_usage_mb,
                "recent_processing_times": list(aggregate.recent_processing_times),
            }

    def get_recent_workflows(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get recent workflow metrics.

        Args:
            limit: Maximum number of recent workflows to return

        Returns:
            List of recent workflow metrics dictionaries
        """
        with self._lock:
            recent = list(self._workflow_metrics)[-limit:]
            return [
                {
                    "workflow_id": str(wm.workflow_id),
                    "workflow_type": wm.workflow_type,
                    "processing_time_ms": wm.processing_time_ms,
                    "memory_usage_mb": wm.memory_usage_mb,
                    "success": wm.success,
                    "error_type": wm.error_info.error_type,
                    "has_error": wm.error_info.has_error,
                    "error_message": wm.error_info.error_message,
                    "started_at": wm.timing.started_at,
                    "completed_at": wm.timing.completed_at,
                    "is_completed": wm.timing.is_completed,
                }
                for wm in recent
            ]

    def reset_metrics(self) -> None:
        """Reset all collected metrics. Used primarily for testing."""
        with self._lock:
            self._workflow_metrics.clear()
            self._aggregate_metrics.clear()
            self._system_metrics.clear()
            self._start_time = time.time()
            self._update_system_metrics()

            emit_log_event(level=LogLevel.INFO, message="Metrics reset")

    def _update_aggregate_metrics(self, workflow_metrics: WorkflowMetrics) -> None:
        """Update aggregate metrics with new workflow data."""
        aggregate = self._aggregate_metrics[workflow_metrics.workflow_type]
        aggregate.workflow_type = workflow_metrics.workflow_type

        if workflow_metrics.success:
            aggregate.successful_count += 1
        else:
            aggregate.failed_count += 1

        aggregate.total_processed += 1
        aggregate.total_processing_time_ms += workflow_metrics.processing_time_ms
        aggregate.total_memory_usage_mb += workflow_metrics.memory_usage_mb

        # Update min/max processing times
        aggregate.min_processing_time_ms = min(
            aggregate.min_processing_time_ms,
            workflow_metrics.processing_time_ms,
        )
        aggregate.max_processing_time_ms = max(
            aggregate.max_processing_time_ms,
            workflow_metrics.processing_time_ms,
        )

        # Add to recent processing times
        aggregate.recent_processing_times.append(workflow_metrics.processing_time_ms)

    def _update_system_metrics(self) -> None:
        """Update system-level metrics."""
        try:
            if not HAS_PSUTIL:
                self._system_metrics.update(
                    {
                        "cpu_percent": 0.0,
                        "memory_usage_mb": 0.0,
                        "memory_percent": 0.0,
                        "num_threads": 0,
                        "num_fds": 0,
                        "create_time": 0.0,
                        "status": "unknown",
                    },
                )
                return

            process = psutil.Process()
            self._system_metrics.update(
                {
                    "cpu_percent": process.cpu_percent(),
                    "memory_usage_mb": self._get_memory_usage_mb(),
                    "memory_percent": process.memory_percent(),
                    "num_threads": process.num_threads(),
                    "num_fds": process.num_fds() if hasattr(process, "num_fds") else 0,
                    "create_time": process.create_time(),
                    "status": process.status(),
                },
            )
        except Exception as e:
            emit_log_event(
                level=LogLevel.WARNING,
                message=f"Failed to update system metrics: {e!s}",
            )

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        try:
            if not HAS_PSUTIL:
                return 0.0
            process = psutil.Process()
            return process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB
        except Exception:
            return 0.0

    def _calculate_overall_success_rate(self) -> float:
        """Calculate overall success rate across all workflow types."""
        total_processed = sum(
            agg.total_processed for agg in self._aggregate_metrics.values()
        )
        total_successful = sum(
            agg.successful_count for agg in self._aggregate_metrics.values()
        )

        if total_processed == 0:
            return 0.0

        return (total_successful / total_processed) * 100.0
