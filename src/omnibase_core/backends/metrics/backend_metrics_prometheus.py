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
        backend.push()  # Push to gateway

.. versionadded:: 0.5.7
"""

from __future__ import annotations

__all__ = [
    "BackendMetricsPrometheus",
    "sanitize_url",
]

import logging
import time
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

# Type variable for generic metric types
_MetricT = TypeVar("_MetricT")

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


def sanitize_url(url: str | None) -> str:
    """
    Remove credentials from URL for safe logging.

    Strips password (and optionally username) from URLs to prevent
    credential leakage in logs, error messages, and monitoring systems.
    Works with any URL scheme (http, https, redis, etc.).

    Args:
        url: Connection URL, potentially containing credentials.
            Format: scheme://[username:password@]host[:port][/path]
            If None, returns "<no-url>".

    Returns:
        Sanitized URL with credentials replaced by '***'.
        Returns '<url-parse-error>' if parsing fails, or original URL if no credentials present.
        Returns '<no-url>' if url is None.

    Example:
        >>> sanitize_url("http://user:secretpass@gateway:9091/metrics")
        'http://***:***@gateway:9091/metrics'
        >>> sanitize_url("https://admin:pass@pushgateway.example.com:9091")
        'https://***:***@pushgateway.example.com:9091'
        >>> sanitize_url("http://localhost:9091")
        'http://localhost:9091'
        >>> sanitize_url(None)
        '<no-url>'

    .. versionadded:: 0.5.7
    """
    if url is None:
        return "<no-url>"

    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            # Reconstruct netloc with masked credentials
            safe_netloc = "***:***@"
            if parsed.hostname:
                safe_netloc += parsed.hostname
            if parsed.port:
                safe_netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=safe_netloc))
        return url
    except Exception:  # fmt: skip  # fallback-ok: URL sanitization must never fail
        # If URL parsing fails, return a generic safe string
        return "<url-parse-error>"


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

    # Default configuration for push gateway retry behavior
    DEFAULT_PUSH_RETRY_COUNT: int = 3
    DEFAULT_PUSH_RETRY_DELAY: float = 0.5
    DEFAULT_PUSH_RETRY_BACKOFF: float = 2.0

    # Cardinality warning threshold
    DEFAULT_CARDINALITY_WARNING_THRESHOLD: int = 100

    def __init__(
        self,
        prefix: str = "",
        registry: CollectorRegistryType | None = None,
        push_gateway_url: str | None = None,
        push_job_name: str = "onex_metrics",
        default_histogram_buckets: tuple[float, ...] | None = None,
        push_retry_count: int | None = None,
        push_retry_delay: float | None = None,
        push_retry_backoff: float | None = None,
        cardinality_warning_threshold: int | None = None,
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
            push_retry_count: Number of retry attempts for push gateway (default: 3)
            push_retry_delay: Initial delay between retries in seconds (default: 0.5)
            push_retry_backoff: Backoff multiplier for retry delay (default: 2.0)
            cardinality_warning_threshold: Threshold for cardinality warnings (default: 100)

        Raises:
            ImportError: If prometheus-client is not installed
        """
        if not PROMETHEUS_AVAILABLE:
            msg = (
                "prometheus-client is required for BackendMetricsPrometheus. "
                "Install with: poetry add prometheus-client "
                "or: poetry install --extras metrics"
            )
            raise ImportError(msg)  # error-ok: standard pattern for optional imports

        self._prefix = prefix
        self._registry: CollectorRegistryType = registry or CollectorRegistry()
        self._push_gateway_url = push_gateway_url
        self._push_job_name = push_job_name
        self._default_buckets = default_histogram_buckets

        # Push gateway retry configuration
        self._push_retry_count = (
            push_retry_count
            if push_retry_count is not None
            else self.DEFAULT_PUSH_RETRY_COUNT
        )
        self._push_retry_delay = (
            push_retry_delay
            if push_retry_delay is not None
            else self.DEFAULT_PUSH_RETRY_DELAY
        )
        self._push_retry_backoff = (
            push_retry_backoff
            if push_retry_backoff is not None
            else self.DEFAULT_PUSH_RETRY_BACKOFF
        )
        self._cardinality_warning_threshold = (
            cardinality_warning_threshold
            if cardinality_warning_threshold is not None
            else self.DEFAULT_CARDINALITY_WARNING_THRESHOLD
        )

        # Caches for metric instances (name -> metric)
        self._gauges: dict[str, Gauge] = {}
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}

        # Track label names for each metric
        self._gauge_labels: dict[str, tuple[str, ...]] = {}
        self._counter_labels: dict[str, tuple[str, ...]] = {}
        self._histogram_labels: dict[str, tuple[str, ...]] = {}

        # Track observed tag value combinations for all metric types (for cardinality tracking)
        # Maps metric name -> set of frozenset of (label_name, label_value) tuples
        self._gauge_tag_combinations: dict[str, set[frozenset[tuple[str, str]]]] = {}
        self._counter_tag_combinations: dict[str, set[frozenset[tuple[str, str]]]] = {}
        self._histogram_tag_combinations: dict[
            str, set[frozenset[tuple[str, str]]]
        ] = {}

        # Track push gateway failures for circuit breaker behavior
        self._consecutive_push_failures: int = 0
        self._last_push_failure_time: float | None = None

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
            self._track_tag_combination(
                full_name, tags, self._gauge_tag_combinations, "gauge"
            )
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
            self._track_tag_combination(
                full_name, tags, self._counter_tag_combinations, "counter"
            )
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
            self._track_tag_combination(
                full_name, tags, self._histogram_tag_combinations, "histogram"
            )
            histogram.labels(**tags).observe(value)
        else:
            histogram.observe(value)

    def push(self) -> None:
        """
        Push metrics to Prometheus push gateway with retry logic.

        If no push gateway URL is configured, this method returns silently.
        Push failures are caught and logged with detailed error information,
        not propagated. Uses exponential backoff for retries.
        """
        if not self._push_gateway_url or not self._push_job_name:
            return

        last_exception: Exception | None = None
        delay = self._push_retry_delay

        for attempt in range(self._push_retry_count):
            try:
                push_to_gateway(
                    self._push_gateway_url,
                    job=self._push_job_name,
                    registry=self._registry,
                )
                # Reset failure tracking on success
                if self._consecutive_push_failures > 0:
                    logger.info(
                        "Push gateway connection restored after %d consecutive failures",
                        self._consecutive_push_failures,
                    )
                self._consecutive_push_failures = 0
                self._last_push_failure_time = None
                return
            except Exception as e:
                # catch-all-ok: retry loop captures failures for exponential backoff
                last_exception = e
                if attempt < self._push_retry_count - 1:
                    logger.debug(
                        "Push attempt %d/%d failed for gateway at %s: %s. "
                        "Retrying in %.2f seconds...",
                        attempt + 1,
                        self._push_retry_count,
                        sanitize_url(self._push_gateway_url),
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= self._push_retry_backoff

        # All retries exhausted
        self._consecutive_push_failures += 1
        self._last_push_failure_time = time.time()

        # Format detailed error message
        error_details = self._format_push_failure_error(last_exception)
        logger.warning(
            "Failed to push metrics to gateway at %s after %d attempts. "
            "Consecutive failures: %d. Error: %s",
            sanitize_url(self._push_gateway_url),
            self._push_retry_count,
            self._consecutive_push_failures,
            error_details,
        )

    def _format_push_failure_error(self, exception: Exception | None) -> str:
        """
        Format a detailed error message for push gateway failures.

        Args:
            exception: The exception that caused the failure

        Returns:
            Formatted error message with troubleshooting hints.
        """
        if exception is None:
            return "Unknown error"

        error_type = type(exception).__name__
        error_msg = str(exception)

        # Provide hints based on common error types
        hints: list[str] = []

        if "Connection refused" in error_msg or "ConnectionError" in error_type:
            hints.append("Check if push gateway is running and accessible")
            hints.append(f"Verify URL: {sanitize_url(self._push_gateway_url)}")
        elif "timeout" in error_msg.lower() or "Timeout" in error_type:
            hints.append("Push gateway may be overloaded or network is slow")
            hints.append("Consider increasing timeout or reducing push frequency")
        elif "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg:
            hints.append("Check push gateway authentication configuration")
        elif "404" in error_msg:
            hints.append("Check push gateway URL path")
            hints.append(f"Current URL: {sanitize_url(self._push_gateway_url)}")

        base_msg = f"{error_type}: {error_msg}"
        if hints:
            return f"{base_msg}. Hints: {'; '.join(hints)}"
        return base_msg

    def get_push_failure_stats(self) -> dict[str, int | float | None]:
        """
        Get statistics about push gateway failures.

        Returns:
            Dictionary with consecutive_failures and last_failure_time.
        """
        return {
            "consecutive_failures": self._consecutive_push_failures,
            "last_failure_time": self._last_push_failure_time,
        }

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

    def _validate_and_get_cached_metric(
        self,
        name: str,
        label_names: tuple[str, ...],
        metric_cache: dict[str, _MetricT],
        label_cache: dict[str, tuple[str, ...]],
        metric_type: str,
    ) -> _MetricT | None:
        """
        Validate labels and return cached metric if it exists.

        This is a common helper for all metric types that handles:
        - Checking if metric exists in cache
        - Validating that label names match if metric exists
        - Raising helpful error if labels mismatch

        Args:
            name: Full metric name
            label_names: Tuple of label names to validate
            metric_cache: Cache dictionary for this metric type
            label_cache: Label cache dictionary for this metric type
            metric_type: Type name for error messages (Gauge, Counter, Histogram)

        Returns:
            Cached metric if found with matching labels, None if not found.

        Raises:
            ValueError: If metric exists with different label names
        """
        if name in metric_cache:
            expected_labels = label_cache.get(name)
            if expected_labels != label_names:
                raise ValueError(  # error-ok: Prometheus label validation error
                    self._format_label_mismatch_error(
                        metric_type=metric_type,
                        name=name,
                        expected_labels=expected_labels,
                        provided_labels=label_names,
                    )
                )
            return metric_cache[name]
        return None

    def _cache_metric(
        self,
        name: str,
        label_names: tuple[str, ...],
        metric: _MetricT,
        metric_cache: dict[str, _MetricT],
        label_cache: dict[str, tuple[str, ...]],
    ) -> None:
        """
        Cache a newly created metric and its labels.

        Args:
            name: Full metric name
            label_names: Tuple of label names
            metric: The metric instance to cache
            metric_cache: Cache dictionary for this metric type
            label_cache: Label cache dictionary for this metric type
        """
        metric_cache[name] = metric
        label_cache[name] = label_names

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
        cached = self._validate_and_get_cached_metric(
            name, label_names, self._gauges, self._gauge_labels, "Gauge"
        )
        if cached is not None:
            return cached

        gauge = Gauge(
            name,
            f"Gauge metric: {name}",
            labelnames=list(label_names),
            registry=self._registry,
        )
        self._cache_metric(name, label_names, gauge, self._gauges, self._gauge_labels)
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
        cached = self._validate_and_get_cached_metric(
            name, label_names, self._counters, self._counter_labels, "Counter"
        )
        if cached is not None:
            return cached

        counter = Counter(
            name,
            f"Counter metric: {name}",
            labelnames=list(label_names),
            registry=self._registry,
        )
        self._cache_metric(
            name, label_names, counter, self._counters, self._counter_labels
        )
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
        cached = self._validate_and_get_cached_metric(
            name, label_names, self._histograms, self._histogram_labels, "Histogram"
        )
        if cached is not None:
            return cached

        kwargs: dict[str, object] = {
            "name": name,
            "documentation": f"Histogram metric: {name}",
            "labelnames": list(label_names),
            "registry": self._registry,
        }
        if self._default_buckets:
            kwargs["buckets"] = self._default_buckets

        # NOTE(OMN-1302): Prometheus Histogram accepts typed kwargs. Safe because kwargs validated above.
        histogram = Histogram(**kwargs)  # type: ignore[arg-type]
        self._cache_metric(
            name, label_names, histogram, self._histograms, self._histogram_labels
        )
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

        Provides specific details about:
        - Which labels are missing (in expected but not provided)
        - Which labels are extra (in provided but not expected)
        - Guidance on how to fix the issue

        Args:
            metric_type: Type of metric (Gauge, Counter, Histogram)
            name: Full metric name
            expected_labels: Labels the metric was registered with
            provided_labels: Labels provided in this call

        Returns:
            Formatted error message with guidance on how to fix the issue.
        """
        expected_set = set(expected_labels) if expected_labels else set()
        provided_set = set(provided_labels) if provided_labels else set()

        # Calculate specific differences
        missing_labels = expected_set - provided_set
        extra_labels = provided_set - expected_set

        # Format the label sets for display
        expected_str = (
            f"[{', '.join(repr(label) for label in sorted(expected_labels))}]"
            if expected_labels
            else "[no labels]"
        )
        provided_str = (
            f"[{', '.join(repr(label) for label in sorted(provided_labels))}]"
            if provided_labels
            else "[no labels]"
        )

        # Build the error message with clear structure
        lines = [
            f"PROMETHEUS LABEL MISMATCH for {metric_type.lower()} metric '{name}'",
            "",
            f"  First registration used labels: {expected_str}",
            f"  This call provided labels:      {provided_str}",
        ]

        # Add specific difference details
        if missing_labels:
            missing_str = ", ".join(repr(label) for label in sorted(missing_labels))
            lines.append(f"  Missing labels (required but not provided): {missing_str}")
        if extra_labels:
            extra_str = ", ".join(repr(label) for label in sorted(extra_labels))
            lines.append(f"  Extra labels (provided but not expected): {extra_str}")

        # Add guidance section
        lines.extend(
            [
                "",
                "HOW TO FIX:",
                "  1. Find all places where this metric is recorded",
                "  2. Ensure ALL calls use the EXACT same set of label keys",
                "  3. If different labels are needed, use a different metric name",
                "",
                "WHY THIS HAPPENS:",
                "  Prometheus requires consistent label names for each metric.",
                "  The first call to record a metric defines its label schema.",
                "  All subsequent calls must use the same label keys (values can differ).",
            ]
        )

        return "\n".join(lines)

    def _track_tag_combination(
        self,
        name: str,
        tags: dict[str, str],
        combinations_store: dict[str, set[frozenset[tuple[str, str]]]],
        metric_type: str,
    ) -> None:
        """
        Track tag value combinations for any metric type and warn on high cardinality.

        This helps identify potential cardinality issues or inconsistent tag usage
        across the codebase. Warns when cardinality exceeds threshold.

        Args:
            name: Full metric name
            tags: Tags provided for this operation
            combinations_store: The dictionary storing combinations for this metric type
            metric_type: Type name for logging (e.g., "counter", "gauge", "histogram")
        """
        # Create a frozenset of (key, value) tuples for hashability
        tag_combination = frozenset(tags.items())

        if name not in combinations_store:
            combinations_store[name] = set()

        existing_combinations = combinations_store[name]

        if tag_combination not in existing_combinations:
            existing_combinations.add(tag_combination)
            combination_count = len(existing_combinations)

            # Log at different levels based on cardinality
            if combination_count == self._cardinality_warning_threshold:
                logger.warning(
                    "High cardinality warning for %s '%s': %d unique tag combinations. "
                    "This may cause memory issues in Prometheus. "
                    "Consider reducing label cardinality by using bounded values.",
                    metric_type,
                    name,
                    combination_count,
                )
            elif combination_count > 1:
                # Log new combinations at debug level
                sorted_tags = dict(sorted(tags.items()))
                logger.debug(
                    "New tag combination for %s '%s': %s (total: %d combinations)",
                    metric_type,
                    name,
                    sorted_tags,
                    combination_count,
                )

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

    def get_gauge_tag_combinations(
        self, name: str
    ) -> set[frozenset[tuple[str, str]]] | None:
        """
        Get observed tag value combinations for a gauge.

        Useful for testing and monitoring cardinality.

        Args:
            name: Metric name (without prefix - will be added automatically)

        Returns:
            Set of observed tag combinations, or None if gauge not found.
        """
        full_name = self._make_name(name)
        return self._gauge_tag_combinations.get(full_name)

    def get_histogram_tag_combinations(
        self, name: str
    ) -> set[frozenset[tuple[str, str]]] | None:
        """
        Get observed tag value combinations for a histogram.

        Useful for testing and monitoring cardinality.

        Args:
            name: Metric name (without prefix - will be added automatically)

        Returns:
            Set of observed tag combinations, or None if histogram not found.
        """
        full_name = self._make_name(name)
        return self._histogram_tag_combinations.get(full_name)

    def get_all_tag_combinations(
        self,
    ) -> dict[str, dict[str, set[frozenset[tuple[str, str]]]]]:
        """
        Get all observed tag value combinations for all metric types.

        Useful for cardinality monitoring and debugging.

        Returns:
            Dictionary with keys 'gauge', 'counter', 'histogram', each containing
            a dict of metric name -> set of tag combinations.
        """
        return {
            "gauge": dict(self._gauge_tag_combinations),
            "counter": dict(self._counter_tag_combinations),
            "histogram": dict(self._histogram_tag_combinations),
        }

    def get_cardinality_report(self) -> dict[str, dict[str, int]]:
        """
        Get a cardinality report showing unique tag combinations per metric.

        Returns:
            Dictionary with keys 'gauge', 'counter', 'histogram', each containing
            a dict of metric name -> count of unique combinations.
        """
        return {
            "gauge": {
                name: len(combos)
                for name, combos in self._gauge_tag_combinations.items()
            },
            "counter": {
                name: len(combos)
                for name, combos in self._counter_tag_combinations.items()
            },
            "histogram": {
                name: len(combos)
                for name, combos in self._histogram_tag_combinations.items()
            },
        }
