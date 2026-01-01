"""
BackendMetricsPrometheus - Prometheus metrics backend implementation.

This backend sends metrics to Prometheus using the prometheus-client library.
It supports gauges, counters, and histograms with optional push gateway support.

Dependencies:
    This module requires the prometheus-client package to be installed:
        poetry add prometheus-client
    or install with the metrics extra:
        poetry install --extras metrics

Thread Safety:
    The prometheus-client library handles thread safety for metric operations.
    However, metric registration (creating new metrics) should be done at
    initialization time, not concurrently.

Usage:
    .. code-block:: python

        from omnibase_core.backends.metrics import BackendMetricsPrometheus

        # Create backend with optional prefix
        backend = BackendMetricsPrometheus(prefix="myapp")

        # Record metrics
        backend.record_gauge("memory_usage_bytes", 1024000)
        backend.increment_counter("requests_total", tags={"method": "GET"})
        backend.record_histogram("request_duration_seconds", 0.15)

        # For push gateway (optional)
        backend = BackendMetricsPrometheus(
            prefix="myapp",
            push_gateway_url="http://localhost:9091",
            push_job_name="my_batch_job",
        )
        backend.record_gauge("batch_progress", 0.75)
        success = backend.push()  # Push to gateway, returns True on success

.. versionadded:: 0.5.7
"""

from __future__ import annotations

__all__ = [
    "BackendMetricsPrometheus",
]

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# Attempt to import prometheus_client, fail gracefully if not installed
try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        push_to_gateway,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if TYPE_CHECKING:
    from prometheus_client import CollectorRegistry as CollectorRegistryType


class BackendMetricsPrometheus:
    """
    Prometheus metrics backend implementation.

    Uses prometheus-client library to create and manage Prometheus metrics.
    Supports optional push gateway for batch job metrics.

    Attributes:
        prefix: Optional prefix for all metric names
        registry: Prometheus collector registry
        push_gateway_url: Optional push gateway URL
        push_job_name: Job name for push gateway

    Thread Safety:
        Metric operations are thread-safe via prometheus-client.
        Metric registration should be done at initialization.

    Example:
        .. code-block:: python

            backend = BackendMetricsPrometheus(prefix="myservice")
            backend.record_gauge("active_connections", 42)
            backend.increment_counter("requests_total", tags={"status": "200"})

            # With push gateway
            backend = BackendMetricsPrometheus(
                push_gateway_url="http://pushgateway:9091",
                push_job_name="my_job",
            )
            backend.record_gauge("job_progress", 0.5)
            backend.push()

    Raises:
        ImportError: If prometheus-client is not installed

    .. versionadded:: 0.5.7
    """

    def __init__(
        self,
        prefix: str = "",
        registry: CollectorRegistryType | None = None,
        push_gateway_url: str | None = None,
        push_job_name: str = "onex_metrics",
        default_histogram_buckets: tuple[float, ...] | None = None,
    ) -> None:
        """
        Initialize the Prometheus metrics backend.

        Args:
            prefix: Optional prefix for all metric names (e.g., "myapp_")
            registry: Custom Prometheus CollectorRegistry, or None for new one
            push_gateway_url: Optional URL for Prometheus push gateway
            push_job_name: Job name when pushing to gateway (default: "onex_metrics")
            default_histogram_buckets: Default histogram buckets (uses Prometheus
                defaults if not specified)

        Raises:
            ImportError: If prometheus-client is not installed
        """
        if not PROMETHEUS_AVAILABLE:
            msg = (
                "prometheus-client is required for BackendMetricsPrometheus. "
                "Install with: poetry add prometheus-client "
                "or: poetry install --extras metrics"
            )
            raise ImportError(msg)

        self._prefix = prefix
        self._registry: CollectorRegistryType = registry or CollectorRegistry()
        self._push_gateway_url = push_gateway_url
        self._push_job_name = push_job_name
        self._default_buckets = default_histogram_buckets

        # Caches for metric instances (name -> metric)
        self._gauges: dict[str, Gauge] = {}
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

        # Track label names for each metric
        self._gauge_labels: dict[str, tuple[str, ...]] = {}
        self._counter_labels: dict[str, tuple[str, ...]] = {}
        self._histogram_labels: dict[str, tuple[str, ...]] = {}

        # Track observed tag value combinations for counters (for consistency warnings)
        # Maps counter name -> set of frozenset of (label_name, label_value) tuples
        self._counter_tag_combinations: dict[str, set[frozenset[tuple[str, str]]]] = {}

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a gauge metric value.

        Args:
            name: Name of the gauge metric
            value: Current value
            tags: Optional labels/tags for the metric
        """
        full_name = self._make_name(name)
        label_names = tuple(sorted(tags.keys())) if tags else ()

        gauge = self._get_or_create_gauge(full_name, label_names)

        if tags:
            gauge.labels(**tags).set(value)
        else:
            gauge.set(value)

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Increment a counter metric.

        Args:
            name: Name of the counter metric
            value: Amount to increment by (default: 1.0)
            tags: Optional labels/tags for the metric
        """
        full_name = self._make_name(name)
        label_names = tuple(sorted(tags.keys())) if tags else ()

        counter = self._get_or_create_counter(full_name, label_names)

        # Track tag value combinations and warn on new combinations
        if tags:
            self._track_counter_tag_combination(full_name, tags)
            counter.labels(**tags).inc(value)
        else:
            counter.inc(value)

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: dict[str, str] | None = None,
    ) -> None:
        """
        Record a histogram observation.

        Args:
            name: Name of the histogram metric
            value: Observed value
            tags: Optional labels/tags for the metric
        """
        full_name = self._make_name(name)
        label_names = tuple(sorted(tags.keys())) if tags else ()

        histogram = self._get_or_create_histogram(full_name, label_names)

        if tags:
            histogram.labels(**tags).observe(value)
        else:
            histogram.observe(value)

    def push(self) -> bool:
        """
        Push metrics to Prometheus push gateway.

        If no push gateway URL is configured, this method returns False.
        Push failures are caught and logged, not propagated.

        Returns:
            True if push was successful, False if no gateway configured or push failed.
        """
        if not self._push_gateway_url or not self._push_job_name:
            return False

        try:
            push_to_gateway(
                self._push_gateway_url,
                job=self._push_job_name,
                registry=self._registry,
            )
            return True
        except Exception as e:
            logger.warning(
                "Failed to push metrics to gateway at %s: %s",
                self._push_gateway_url,
                e,
            )
            return False

    def get_registry(self) -> CollectorRegistryType:
        """
        Get the underlying Prometheus registry.

        Returns:
            The CollectorRegistry used by this backend.
        """
        return self._registry

    def _make_name(self, name: str) -> str:
        """
        Create full metric name with optional prefix.

        Args:
            name: Base metric name

        Returns:
            Full metric name with prefix if configured.
        """
        if self._prefix:
            # Ensure proper underscore separation
            prefix = self._prefix.rstrip("_")
            return f"{prefix}_{name}"
        return name

    def _get_or_create_gauge(self, name: str, label_names: tuple[str, ...]) -> Gauge:
        """
        Get existing gauge or create new one.

        Args:
            name: Full metric name
            label_names: Tuple of label names

        Returns:
            Gauge metric instance.

        Raises:
            ValueError: If metric exists with different label names
        """
        if name in self._gauges:
            expected_labels = self._gauge_labels.get(name)
            if expected_labels != label_names:
                raise ValueError(
                    self._format_label_mismatch_error(
                        metric_type="Gauge",
                        name=name,
                        expected_labels=expected_labels,
                        provided_labels=label_names,
                    )
                )
            return self._gauges[name]

        gauge = Gauge(
            name,
            f"Gauge metric: {name}",
            labelnames=list(label_names),
            registry=self._registry,
        )
        self._gauges[name] = gauge
        self._gauge_labels[name] = label_names
        return gauge

    def _get_or_create_counter(
        self, name: str, label_names: tuple[str, ...]
    ) -> Counter:
        """
        Get existing counter or create new one.

        Args:
            name: Full metric name
            label_names: Tuple of label names

        Returns:
            Counter metric instance.

        Raises:
            ValueError: If metric exists with different label names
        """
        if name in self._counters:
            expected_labels = self._counter_labels.get(name)
            if expected_labels != label_names:
                raise ValueError(
                    self._format_label_mismatch_error(
                        metric_type="Counter",
                        name=name,
                        expected_labels=expected_labels,
                        provided_labels=label_names,
                    )
                )
            return self._counters[name]

        counter = Counter(
            name,
            f"Counter metric: {name}",
            labelnames=list(label_names),
            registry=self._registry,
        )
        self._counters[name] = counter
        self._counter_labels[name] = label_names
        return counter

    def _get_or_create_histogram(
        self, name: str, label_names: tuple[str, ...]
    ) -> Histogram:
        """
        Get existing histogram or create new one.

        Args:
            name: Full metric name
            label_names: Tuple of label names

        Returns:
            Histogram metric instance.

        Raises:
            ValueError: If metric exists with different label names
        """
        if name in self._histograms:
            expected_labels = self._histogram_labels.get(name)
            if expected_labels != label_names:
                raise ValueError(
                    self._format_label_mismatch_error(
                        metric_type="Histogram",
                        name=name,
                        expected_labels=expected_labels,
                        provided_labels=label_names,
                    )
                )
            return self._histograms[name]

        kwargs: dict[str, object] = {
            "name": name,
            "documentation": f"Histogram metric: {name}",
            "labelnames": list(label_names),
            "registry": self._registry,
        }
        if self._default_buckets:
            kwargs["buckets"] = self._default_buckets

        histogram = Histogram(**kwargs)  # type: ignore[arg-type]
        self._histograms[name] = histogram
        self._histogram_labels[name] = label_names
        return histogram

    def _format_label_mismatch_error(
        self,
        metric_type: str,
        name: str,
        expected_labels: tuple[str, ...] | None,
        provided_labels: tuple[str, ...],
    ) -> str:
        """
        Format a helpful error message for label mismatches.

        Args:
            metric_type: Type of metric (Gauge, Counter, Histogram)
            name: Full metric name
            expected_labels: Labels the metric was registered with
            provided_labels: Labels provided in this call

        Returns:
            Formatted error message with guidance on how to fix the issue.
        """
        expected_str = (
            f"({', '.join(repr(l) for l in expected_labels)})"
            if expected_labels
            else "(no labels)"
        )
        provided_str = (
            f"({', '.join(repr(l) for l in provided_labels)})"
            if provided_labels
            else "(no labels)"
        )

        return (
            f"Label mismatch for {metric_type.lower()} metric '{name}': "
            f"expected labels {expected_str}, got {provided_str}. "
            f"Prometheus requires consistent label names across all recordings of a metric. "
            f"To fix this issue: ensure all calls to record this metric use the same set of "
            f"label keys. If you need different labels, use a different metric name."
        )

    def _track_counter_tag_combination(self, name: str, tags: dict[str, str]) -> None:
        """
        Track tag value combinations for a counter and warn on new combinations.

        This helps identify potential cardinality issues or inconsistent tag usage
        across the codebase.

        Args:
            name: Full metric name
            tags: Tags provided for this increment
        """
        # Create a frozenset of (key, value) tuples for hashability
        tag_combination = frozenset(tags.items())

        if name not in self._counter_tag_combinations:
            self._counter_tag_combinations[name] = set()

        existing_combinations = self._counter_tag_combinations[name]

        if tag_combination not in existing_combinations:
            # This is a new tag value combination
            if existing_combinations:
                # Warn only if there are already existing combinations
                # (first combination is expected, subsequent ones are noteworthy)
                sorted_tags = dict(sorted(tags.items()))
                logger.debug(
                    "New tag value combination observed for counter '%s': %s. "
                    "Previously seen %d different combination(s). "
                    "Consider if this indicates high cardinality.",
                    name,
                    sorted_tags,
                    len(existing_combinations),
                )
            existing_combinations.add(tag_combination)

    def get_counter_tag_combinations(
        self, name: str
    ) -> set[frozenset[tuple[str, str]]] | None:
        """
        Get observed tag value combinations for a counter.

        Useful for testing and monitoring cardinality.

        Args:
            name: Metric name (without prefix - will be added automatically)

        Returns:
            Set of observed tag combinations, or None if counter not found.
        """
        full_name = self._make_name(name)
        return self._counter_tag_combinations.get(full_name)
