#!/usr/bin/env python3
"""
Metrics collection system for canary nodes.

Provides comprehensive performance monitoring, alerting, and observability
for canary deployment monitoring and analysis.
"""

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.nodes.canary.config.canary_config import get_canary_config


@dataclass
class MetricPoint:
    """Individual metric measurement point."""

    timestamp: float
    value: Union[int, float]
    labels: Dict[str, str]


class ModelMetricSummary(BaseModel):
    """Summary statistics for a metric."""

    count: int
    sum: float
    min: float
    max: float
    avg: float
    p50: float
    p95: float
    p99: float


class ModelNodeMetrics(BaseModel):
    """Comprehensive metrics for a canary node."""

    # Operation metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    # Performance metrics
    avg_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0

    # Error metrics
    error_rate: float = 0.0
    timeout_count: int = 0
    circuit_breaker_trips: int = 0

    # Resource metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Health metrics
    health_score: float = 1.0
    degraded_periods: int = 0

    # Business metrics (operation-specific)
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics for canary nodes.

    Provides real-time metrics collection, aggregation, and alerting
    for comprehensive canary deployment monitoring.
    """

    def __init__(self, node_name: str, max_points: int = 10000):
        self.node_name = node_name
        self.config = get_canary_config()
        self.max_points = max_points

        # Metric storage
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_points))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = defaultdict(float)
        self._histograms: Dict[str, List[float]] = defaultdict(list)

        # Operation tracking
        self._operation_start_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def record_operation_start(
        self, operation_id: str, operation_type: str
    ) -> None:
        """Record the start of an operation for latency tracking."""
        async with self._lock:
            self._operation_start_times[operation_id] = time.time()
            self.increment_counter("operations.started", {"type": operation_type})

    async def record_operation_end(
        self,
        operation_id: str,
        operation_type: str,
        success: bool,
        error_type: Optional[str] = None,
    ) -> float:
        """
        Record the end of an operation and calculate latency.

        Returns:
            Operation duration in milliseconds
        """
        async with self._lock:
            end_time = time.time()
            start_time = self._operation_start_times.pop(operation_id, end_time)
            duration_ms = (end_time - start_time) * 1000

            # Record latency
            await self.record_histogram(
                "operation.duration_ms",
                duration_ms,
                {"type": operation_type, "success": str(success)},
            )

            # Record success/failure
            if success:
                self.increment_counter("operations.success", {"type": operation_type})
            else:
                self.increment_counter(
                    "operations.failure",
                    {"type": operation_type, "error_type": error_type or "unknown"},
                )

            return duration_ms

    def increment_counter(
        self, metric_name: str, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Increment a counter metric."""
        labels = labels or {}
        key = f"{metric_name}#{self._serialize_labels(labels)}"
        self._counters[key] += 1

    def set_gauge(
        self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Set a gauge metric value."""
        labels = labels or {}
        key = f"{metric_name}#{self._serialize_labels(labels)}"
        self._gauges[key] = value

    async def record_histogram(
        self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a value in a histogram."""
        labels = labels or {}
        key = f"{metric_name}#{self._serialize_labels(labels)}"

        async with self._lock:
            # Add to histogram
            if (
                len(self._histograms[key])
                >= self.config.performance.metrics_retention_count
            ):
                self._histograms[key] = self._histograms[key][
                    -self.config.performance.metrics_retention_count // 2 :
                ]
            self._histograms[key].append(value)

            # Also add to time series
            self._metrics[key].append(
                MetricPoint(timestamp=time.time(), value=value, labels=labels)
            )

    def record_custom_metric(
        self,
        metric_name: str,
        value: Union[int, float],
        metric_type: str = "gauge",
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record a custom business metric."""
        labels = labels or {}

        if metric_type == "counter":
            for _ in range(int(value)):
                self.increment_counter(metric_name, labels)
        elif metric_type == "gauge":
            self.set_gauge(metric_name, float(value), labels)
        elif metric_type == "histogram":
            asyncio.create_task(
                self.record_histogram(metric_name, float(value), labels)
            )

    def get_node_metrics(self) -> ModelNodeMetrics:
        """Get comprehensive metrics summary for the node."""

        # Calculate operation metrics
        total_ops = sum(
            count
            for key, count in self._counters.items()
            if "operations.started" in key
        )
        success_ops = sum(
            count
            for key, count in self._counters.items()
            if "operations.success" in key
        )
        failed_ops = sum(
            count
            for key, count in self._counters.items()
            if "operations.failure" in key
        )

        # Calculate performance metrics
        duration_values = []
        for key, values in self._histograms.items():
            if "operation.duration_ms" in key:
                duration_values.extend(values)

        avg_response_time = (
            sum(duration_values) / len(duration_values) if duration_values else 0.0
        )
        p95_response_time = (
            self._percentile(duration_values, 0.95) if duration_values else 0.0
        )
        p99_response_time = (
            self._percentile(duration_values, 0.99) if duration_values else 0.0
        )

        # Calculate error rate
        error_rate = (failed_ops / max(1, total_ops)) * 100

        # Get resource metrics
        memory_usage = max(
            (value for key, value in self._gauges.items() if "memory.usage_mb" in key),
            default=0.0,
        )

        cpu_usage = max(
            (
                value
                for key, value in self._gauges.items()
                if "cpu.usage_percent" in key
            ),
            default=0.0,
        )

        # Calculate health score (weighted average of key metrics)
        health_score = self._calculate_health_score(error_rate, avg_response_time)

        # Get custom metrics
        custom_metrics = {
            self._extract_metric_name(key): value
            for key, value in self._gauges.items()
            if key.startswith("custom.")
        }

        return ModelNodeMetrics(
            total_operations=total_ops,
            successful_operations=success_ops,
            failed_operations=failed_ops,
            avg_response_time_ms=avg_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            error_rate=error_rate,
            timeout_count=sum(
                count
                for key, count in self._counters.items()
                if "timeout" in key.lower()
            ),
            circuit_breaker_trips=sum(
                count
                for key, count in self._counters.items()
                if "circuit_breaker.trip" in key
            ),
            memory_usage_mb=memory_usage,
            cpu_usage_percent=cpu_usage,
            health_score=health_score,
            custom_metrics=custom_metrics,
        )

    def get_metric_summary(self, metric_name: str) -> Optional[ModelMetricSummary]:
        """Get summary statistics for a specific metric."""
        values = []

        # Collect values from histograms
        for key, histogram_values in self._histograms.items():
            if metric_name in key:
                values.extend(histogram_values)

        # Collect values from time series
        for key, points in self._metrics.items():
            if metric_name in key:
                values.extend([point.value for point in points])

        if not values:
            return None

        sorted_values = sorted(values)

        return ModelMetricSummary(
            count=len(values),
            sum=sum(values),
            min=min(values),
            max=max(values),
            avg=sum(values) / len(values),
            p50=self._percentile(sorted_values, 0.5),
            p95=self._percentile(sorted_values, 0.95),
            p99=self._percentile(sorted_values, 0.99),
        )

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics in a structured format."""
        return {
            "node_name": self.node_name,
            "timestamp": time.time(),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {
                key: {
                    "count": len(values),
                    "avg": sum(values) / len(values) if values else 0,
                    "p95": self._percentile(values, 0.95) if values else 0,
                }
                for key, values in self._histograms.items()
            },
            "node_summary": self.get_node_metrics().model_dump(),
        }

    def reset_metrics(self) -> None:
        """Reset all collected metrics."""
        self._metrics.clear()
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._operation_start_times.clear()

    def _serialize_labels(self, labels: Dict[str, str]) -> str:
        """Serialize labels to a consistent string format."""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _extract_metric_name(self, key: str) -> str:
        """Extract clean metric name from internal key."""
        return key.split("#")[0]

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from sorted values."""
        if not values:
            return 0.0
        index = int(len(values) * percentile)
        return values[min(index, len(values) - 1)]

    def _calculate_health_score(
        self, error_rate: float, avg_response_time: float
    ) -> float:
        """Calculate overall health score based on key metrics."""
        # Start with perfect score
        score = 1.0

        # Penalize for error rate (max penalty: -0.5)
        if error_rate > 0:
            error_penalty = min(error_rate / 100 * 0.5, 0.5)
            score -= error_penalty

        # Penalize for high response times (max penalty: -0.3)
        if avg_response_time > 1000:  # > 1 second
            response_penalty = min((avg_response_time - 1000) / 10000 * 0.3, 0.3)
            score -= response_penalty

        return max(0.0, score)


# Global metrics collectors by node
_metrics_collectors: Dict[str, MetricsCollector] = {}


def get_metrics_collector(node_name: str) -> MetricsCollector:
    """Get or create a metrics collector for a node."""
    if node_name not in _metrics_collectors:
        _metrics_collectors[node_name] = MetricsCollector(node_name)
    return _metrics_collectors[node_name]


def get_all_node_metrics() -> Dict[str, Dict[str, Any]]:
    """Get metrics from all registered nodes."""
    return {
        node_name: collector.get_all_metrics()
        for node_name, collector in _metrics_collectors.items()
    }
