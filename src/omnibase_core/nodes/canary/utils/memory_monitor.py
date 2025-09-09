#!/usr/bin/env python3
"""
Memory monitoring utilities for canary nodes.

Provides memory usage tracking, alerting, and optimization for long-running operations.
"""

import asyncio
import gc
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import psutil

from omnibase_core.utils.security_utils import create_secure_logger


@dataclass
class MemoryMetrics:
    """Memory usage metrics snapshot."""

    timestamp: float
    process_memory_mb: float
    system_memory_percent: float
    available_memory_mb: float
    gc_collections: dict[int, int]
    operation_name: str | None = None


class MemoryMonitor:
    """Memory usage monitor for long-running operations."""

    def __init__(
        self,
        threshold_mb: float = 500.0,
        warning_threshold_percent: float = 80.0,
        check_interval_seconds: float = 5.0,
    ):
        self.threshold_mb = threshold_mb
        self.warning_threshold_percent = warning_threshold_percent
        self.check_interval_seconds = check_interval_seconds
        self.logger = create_secure_logger(self.__class__.__name__)

        self._process = psutil.Process()
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self._baseline_metrics: MemoryMetrics | None = None

    def _get_memory_metrics(
        self,
        operation_name: str | None = None,
    ) -> MemoryMetrics:
        """Get current memory usage metrics.

        Args:
            operation_name: Name of operation being monitored

        Returns:
            Current memory metrics snapshot

        Example:
            >>> monitor = MemoryMonitor()
            >>> metrics = monitor._get_memory_metrics("database_query")
            >>> print(f"Process using {metrics.process_memory_mb:.1f}MB")
            Process using 245.3MB
        """
        try:
            # Process memory info
            memory_info = self._process.memory_info()
            process_memory_mb = memory_info.rss / (1024 * 1024)

            # System memory info
            system_memory = psutil.virtual_memory()
            system_memory_percent = system_memory.percent
            available_memory_mb = system_memory.available / (1024 * 1024)

            # Garbage collection stats
            gc_stats = {i: gc.get_count()[i] for i in range(3)}

            return MemoryMetrics(
                timestamp=time.time(),
                process_memory_mb=process_memory_mb,
                system_memory_percent=system_memory_percent,
                available_memory_mb=available_memory_mb,
                gc_collections=gc_stats,
                operation_name=operation_name,
            )
        except Exception as e:
            self.logger.error(f"Failed to get memory metrics: {e}")
            # Return safe defaults
            return MemoryMetrics(
                timestamp=time.time(),
                process_memory_mb=0.0,
                system_memory_percent=0.0,
                available_memory_mb=0.0,
                gc_collections={0: 0, 1: 0, 2: 0},
            )

    def set_baseline(self, operation_name: str = "baseline") -> MemoryMetrics:
        """Set memory usage baseline for comparison.

        Args:
            operation_name: Name to identify this baseline

        Returns:
            Baseline memory metrics

        Example:
            >>> monitor = MemoryMonitor()
            >>> baseline = monitor.set_baseline("startup")
            >>> # ... do some work ...
            >>> current = monitor._get_memory_metrics("after_work")
            >>> growth = current.process_memory_mb - baseline.process_memory_mb
        """
        self._baseline_metrics = self._get_memory_metrics(operation_name)
        self.logger.info(
            f"Memory baseline set: {self._baseline_metrics.process_memory_mb:.1f}MB "
            f"(system: {self._baseline_metrics.system_memory_percent:.1f}%)",
        )
        return self._baseline_metrics

    def check_memory_usage(
        self,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> bool:
        """Check if memory usage is within acceptable limits.

        Args:
            operation_name: Name of operation being checked
            correlation_id: Optional correlation ID for tracing

        Returns:
            True if memory usage is acceptable, False if over threshold

        Example:
            >>> monitor = MemoryMonitor(threshold_mb=100.0)
            >>> if not monitor.check_memory_usage("heavy_computation", "req-123"):
            ...     print("Memory usage too high, consider optimization")
        """
        try:
            current_metrics = self._get_memory_metrics(operation_name)
            log_context = f"[correlation_id={correlation_id}]" if correlation_id else ""

            # Check process memory threshold
            if current_metrics.process_memory_mb > self.threshold_mb:
                self.logger.warning(
                    f"Process memory usage ({current_metrics.process_memory_mb:.1f}MB) "
                    f"exceeds threshold ({self.threshold_mb:.1f}MB) for {operation_name} {log_context}",
                )
                return False

            # Check system memory threshold
            if current_metrics.system_memory_percent > self.warning_threshold_percent:
                self.logger.warning(
                    f"System memory usage ({current_metrics.system_memory_percent:.1f}%) "
                    f"exceeds warning threshold ({self.warning_threshold_percent:.1f}%) {log_context}",
                )

            # Log memory growth if baseline exists
            if self._baseline_metrics:
                growth_mb = (
                    current_metrics.process_memory_mb
                    - self._baseline_metrics.process_memory_mb
                )
                if growth_mb > 50.0:  # Significant growth threshold
                    self.logger.info(
                        f"Memory growth detected: +{growth_mb:.1f}MB since baseline for {operation_name} {log_context}",
                    )

            return True

        except Exception as e:
            self.logger.error(f"Memory check failed for {operation_name}: {e}")
            return True  # Assume OK if check fails

    async def _monitor_operation(
        self,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> None:
        """Background monitoring task for an operation."""
        try:
            while True:
                self.check_memory_usage(operation_name, correlation_id)
                await asyncio.sleep(self.check_interval_seconds)
        except asyncio.CancelledError:
            self.logger.debug(f"Memory monitoring stopped for {operation_name}")
        except Exception as e:
            self.logger.error(f"Memory monitoring error for {operation_name}: {e}")

    def start_monitoring(
        self,
        operation_name: str,
        correlation_id: str | None = None,
    ) -> str:
        """Start background memory monitoring for an operation.

        Args:
            operation_name: Name of operation to monitor
            correlation_id: Optional correlation ID for tracing

        Returns:
            Monitoring task key for stopping monitoring

        Example:
            >>> monitor = MemoryMonitor()
            >>> task_key = monitor.start_monitoring("long_computation", "req-456")
            >>> # ... operation runs ...
            >>> monitor.stop_monitoring(task_key)
        """
        task_key = f"{operation_name}_{id(self)}"

        if task_key not in self._monitoring_tasks:
            task = asyncio.create_task(
                self._monitor_operation(operation_name, correlation_id),
            )
            self._monitoring_tasks[task_key] = task
            self.logger.debug(f"Started memory monitoring for {operation_name}")

        return task_key

    def stop_monitoring(self, task_key: str) -> bool:
        """Stop background memory monitoring.

        Args:
            task_key: Key returned from start_monitoring

        Returns:
            True if monitoring was stopped, False if not found
        """
        if task_key in self._monitoring_tasks:
            task = self._monitoring_tasks.pop(task_key)
            task.cancel()
            self.logger.debug(f"Stopped memory monitoring for task {task_key}")
            return True
        return False

    async def cleanup(self) -> None:
        """Clean up all monitoring tasks."""
        tasks_to_cancel = list(self._monitoring_tasks.values())
        self._monitoring_tasks.clear()

        for task in tasks_to_cancel:
            task.cancel()

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            self.logger.debug(
                f"Cancelled {len(tasks_to_cancel)} memory monitoring tasks",
            )

    def force_garbage_collection(self, operation_name: str) -> dict[str, Any]:
        """Force garbage collection and return collection stats.

        Args:
            operation_name: Name of operation triggering GC

        Returns:
            Dictionary with GC statistics and memory info

        Example:
            >>> monitor = MemoryMonitor()
            >>> stats = monitor.force_garbage_collection("cleanup_phase")
            >>> print(f"Collected {stats['objects_collected']} objects")
        """
        try:
            before_metrics = self._get_memory_metrics(f"{operation_name}_before_gc")

            # Force garbage collection
            collected_objects = gc.collect()

            after_metrics = self._get_memory_metrics(f"{operation_name}_after_gc")

            memory_freed_mb = (
                before_metrics.process_memory_mb - after_metrics.process_memory_mb
            )

            stats = {
                "operation_name": operation_name,
                "objects_collected": collected_objects,
                "memory_before_mb": before_metrics.process_memory_mb,
                "memory_after_mb": after_metrics.process_memory_mb,
                "memory_freed_mb": memory_freed_mb,
                "timestamp": time.time(),
            }

            self.logger.info(
                f"Garbage collection for {operation_name}: "
                f"collected {collected_objects} objects, "
                f"freed {memory_freed_mb:.1f}MB",
            )

            return stats

        except Exception as e:
            self.logger.error(f"Garbage collection failed for {operation_name}: {e}")
            return {"error": str(e), "operation_name": operation_name}


@asynccontextmanager
async def memory_monitored_operation(
    operation_name: str,
    monitor: MemoryMonitor | None = None,
    correlation_id: str | None = None,
    auto_gc: bool = False,
) -> AsyncGenerator[MemoryMonitor, None]:
    """Context manager for memory-monitored operations.

    Args:
        operation_name: Name of the operation
        monitor: Existing monitor instance (creates new if None)
        correlation_id: Optional correlation ID for tracing
        auto_gc: Whether to run garbage collection after operation

    Yields:
        MemoryMonitor instance for the operation

    Example:
        >>> async with memory_monitored_operation("data_processing", correlation_id="req-789") as monitor:
        ...     # Your long-running operation here
        ...     for chunk in large_dataset:
        ...         process_chunk(chunk)
        ...         if not monitor.check_memory_usage("chunk_processing"):
        ...             break  # Stop if memory usage too high
    """
    if monitor is None:
        monitor = MemoryMonitor()

    # Set baseline and start monitoring
    monitor.set_baseline(f"{operation_name}_start")
    task_key = monitor.start_monitoring(operation_name, correlation_id)

    try:
        yield monitor
    finally:
        # Stop monitoring and cleanup
        monitor.stop_monitoring(task_key)

        # Final memory check
        final_metrics = monitor._get_memory_metrics(f"{operation_name}_end")
        if monitor._baseline_metrics:
            total_growth = (
                final_metrics.process_memory_mb
                - monitor._baseline_metrics.process_memory_mb
            )
            monitor.logger.info(
                f"Operation {operation_name} completed: total memory growth {total_growth:.1f}MB",
            )

        # Optional garbage collection
        if auto_gc:
            monitor.force_garbage_collection(f"{operation_name}_cleanup")


# Global memory monitor instance
_global_monitor: MemoryMonitor | None = None


def get_memory_monitor() -> MemoryMonitor:
    """Get global memory monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = MemoryMonitor()
    return _global_monitor
