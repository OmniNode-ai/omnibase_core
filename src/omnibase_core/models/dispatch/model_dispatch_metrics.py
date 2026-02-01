"""
Dispatch Metrics Model.

Aggregate metrics for the message dispatch engine including dispatch counts,
latency histograms, and per-handler/per-category breakdowns.

Design Pattern:
    ModelDispatchMetrics is a comprehensive metrics container that aggregates:
    - Overall dispatch statistics (counts, latency)
    - Per-handler metrics (via ModelHandlerMetrics)
    - Per-category metrics (event, command, intent counts)
    - Latency histogram buckets for distribution analysis

    Unlike most ONEX models, this is NOT frozen because metrics accumulate
    during dispatch engine operation.

Thread Safety:
    This model is NOT thread-safe on its own. The MessageDispatchEngine provides
    thread-safety guarantees during metrics collection.

Example:
    >>> from omnibase_core.models.dispatch import ModelDispatchMetrics
    >>> from omnibase_core.enums import EnumMessageCategory
    >>>
    >>> metrics = ModelDispatchMetrics()
    >>> metrics = metrics.record_dispatch(
    ...     duration_ms=45.2,
    ...     success=True,
    ...     category=EnumMessageCategory.EVENT,
    ...     handler_id="user-handler",
    ... )
    >>> print(f"Success rate: {metrics.success_rate:.1%}")

See Also:
    omnibase_core.models.dispatch.ModelHandlerMetrics: Per-handler metrics
    omnibase_core.runtime.MessageDispatchEngine: Uses these for observability
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_execution_shape import EnumMessageCategory
from omnibase_core.models.dispatch.model_handler_metrics import ModelHandlerMetrics

# Histogram bucket boundaries in milliseconds
LATENCY_HISTOGRAM_BUCKETS: tuple[float, ...] = (
    1.0,
    5.0,
    10.0,
    25.0,
    50.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10000.0,
)


class ModelDispatchMetrics(BaseModel):
    """
    Aggregate metrics for the message dispatch engine.

    Provides comprehensive observability including:
    - Overall dispatch counts and success/error rates
    - Latency statistics (average, min, max)
    - Latency histogram for distribution analysis
    - Per-handler metrics breakdown
    - Per-category metrics breakdown

    Attributes:
        total_dispatches: Total number of dispatch operations.
        successful_dispatches: Number of successful dispatches.
        failed_dispatches: Number of failed dispatches.
        no_handler_count: Dispatches with no matching handler.
        category_mismatch_count: Dispatches with category validation failures.
        total_latency_ms: Cumulative latency across all dispatches.
        min_latency_ms: Minimum observed dispatch latency.
        max_latency_ms: Maximum observed dispatch latency.
        latency_histogram: Histogram buckets for latency distribution.
        handler_metrics: Per-handler metrics keyed by handler_id.
        category_metrics: Per-category dispatch counts.

    Example:
        >>> metrics = ModelDispatchMetrics()
        >>> print(f"Total dispatches: {metrics.total_dispatches}")
        >>> print(f"Success rate: {metrics.success_rate:.1%}")
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    # ---- Dispatch Counts ----
    total_dispatches: int = Field(
        default=0,
        description="Total number of dispatch operations.",
        ge=0,
    )
    successful_dispatches: int = Field(
        default=0,
        description="Number of successful dispatches.",
        ge=0,
    )
    failed_dispatches: int = Field(
        default=0,
        description="Number of failed dispatches.",
        ge=0,
    )
    no_handler_count: int = Field(
        default=0,
        description="Dispatches with no matching handler.",
        ge=0,
    )
    category_mismatch_count: int = Field(
        default=0,
        description="Dispatches with category validation failures.",
        ge=0,
    )

    # ---- Handler Execution Counts ----
    handler_execution_count: int = Field(
        default=0,
        description="Total number of handler executions (may exceed dispatch count for fan-out).",
        ge=0,
    )
    handler_error_count: int = Field(
        default=0,
        description="Total number of handler execution failures.",
        ge=0,
    )
    routes_matched_count: int = Field(
        default=0,
        description="Total number of route matches.",
        ge=0,
    )

    # ---- Latency Statistics ----
    total_latency_ms: float = Field(
        default=0.0,
        description="Cumulative latency across all dispatches in milliseconds.",
        ge=0,
    )
    min_latency_ms: float | None = Field(
        default=None,
        description="Minimum observed dispatch latency in milliseconds.",
    )
    max_latency_ms: float | None = Field(
        default=None,
        description="Maximum observed dispatch latency in milliseconds.",
    )

    # ---- Latency Histogram ----
    latency_histogram: dict[str, int] = Field(
        default_factory=lambda: {
            "le_1ms": 0,
            "le_5ms": 0,
            "le_10ms": 0,
            "le_25ms": 0,
            "le_50ms": 0,
            "le_100ms": 0,
            "le_250ms": 0,
            "le_500ms": 0,
            "le_1000ms": 0,
            "le_2500ms": 0,
            "le_5000ms": 0,
            "le_10000ms": 0,
            "gt_10000ms": 0,
        },
        description="Histogram buckets for latency distribution.",
    )

    # ---- Per-Handler Metrics ----
    handler_metrics: dict[str, ModelHandlerMetrics] = Field(
        default_factory=dict,
        description="Per-handler metrics keyed by handler_id.",
    )

    # ---- Per-Category Metrics ----
    category_metrics: dict[str, int] = Field(
        default_factory=lambda: {
            "event": 0,
            "command": 0,
            "intent": 0,
        },
        description="Per-category dispatch counts.",
    )

    @property
    def avg_latency_ms(self) -> float:
        """
        Calculate average latency across all dispatches.

        Returns:
            Average latency in milliseconds, or 0.0 if no dispatches.
        """
        if self.total_dispatches == 0:
            return 0.0
        return self.total_latency_ms / self.total_dispatches

    @property
    def success_rate(self) -> float:
        """
        Calculate success rate as a fraction (0.0 to 1.0).

        Returns:
            Success rate as a decimal, or 1.0 if no dispatches.
        """
        if self.total_dispatches == 0:
            return 1.0
        return self.successful_dispatches / self.total_dispatches

    @property
    def error_rate(self) -> float:
        """
        Calculate error rate as a fraction (0.0 to 1.0).

        Returns:
            Error rate as a decimal, or 0.0 if no dispatches.
        """
        if self.total_dispatches == 0:
            return 0.0
        return self.failed_dispatches / self.total_dispatches

    def _get_histogram_bucket(self, duration_ms: float) -> str:
        """Get the histogram bucket key for a given latency."""
        for i, threshold in enumerate(LATENCY_HISTOGRAM_BUCKETS):
            if duration_ms <= threshold:
                # Map threshold to bucket key
                threshold_int = int(threshold)
                return f"le_{threshold_int}ms"
        return "gt_10000ms"

    def record_dispatch(
        self,
        duration_ms: float,
        success: bool,
        category: EnumMessageCategory | None = None,
        handler_id: str | None = None,
        no_handler: bool = False,
        category_mismatch: bool = False,
        handler_error: bool = False,
        routes_matched: int = 0,
        topic: str | None = None,
        error_message: str | None = None,
    ) -> "ModelDispatchMetrics":
        """
        Record a dispatch operation and return updated metrics.

        Creates a new ModelDispatchMetrics instance with updated statistics.

        Args:
            duration_ms: Dispatch duration in milliseconds.
            success: Whether the dispatch was successful.
            category: Optional message category for per-category metrics.
            handler_id: Optional handler ID for per-handler metrics.
            no_handler: Whether no handler was found.
            category_mismatch: Whether category validation failed.
            handler_error: Whether a handler execution error occurred.
            routes_matched: Number of routes that matched.
            topic: Optional topic for handler metrics.
            error_message: Optional error message for handler metrics.

        Returns:
            New ModelDispatchMetrics with updated statistics.
        """
        # Update latency statistics
        new_min = (
            duration_ms
            if self.min_latency_ms is None
            else min(self.min_latency_ms, duration_ms)
        )
        new_max = (
            duration_ms
            if self.max_latency_ms is None
            else max(self.max_latency_ms, duration_ms)
        )

        # Update histogram
        new_histogram = dict(self.latency_histogram)
        bucket = self._get_histogram_bucket(duration_ms)
        new_histogram[bucket] = new_histogram.get(bucket, 0) + 1

        # Update category metrics
        new_category_metrics = dict(self.category_metrics)
        if category is not None:
            category_key = category.value.lower()
            new_category_metrics[category_key] = (
                new_category_metrics.get(category_key, 0) + 1
            )

        # Update handler metrics
        new_handler_metrics = dict(self.handler_metrics)
        if handler_id is not None:
            existing = new_handler_metrics.get(handler_id)
            if existing is None:
                existing = ModelHandlerMetrics(handler_id=handler_id)
            new_handler_metrics[handler_id] = existing.record_execution(
                duration_ms=duration_ms,
                success=success and not handler_error,
                topic=topic,
                error_message=error_message,
            )

        return ModelDispatchMetrics(
            total_dispatches=self.total_dispatches + 1,
            successful_dispatches=self.successful_dispatches + (1 if success else 0),
            failed_dispatches=self.failed_dispatches + (0 if success else 1),
            no_handler_count=self.no_handler_count + (1 if no_handler else 0),
            category_mismatch_count=self.category_mismatch_count
            + (1 if category_mismatch else 0),
            handler_execution_count=self.handler_execution_count
            + (1 if handler_id else 0),
            handler_error_count=self.handler_error_count + (1 if handler_error else 0),
            routes_matched_count=self.routes_matched_count + routes_matched,
            total_latency_ms=self.total_latency_ms + duration_ms,
            min_latency_ms=new_min,
            max_latency_ms=new_max,
            latency_histogram=new_histogram,
            handler_metrics=new_handler_metrics,
            category_metrics=new_category_metrics,
        )

    def get_handler_metrics(self, handler_id: str) -> ModelHandlerMetrics | None:
        """
        Get metrics for a specific handler.

        Args:
            handler_id: The handler's unique identifier.

        Returns:
            ModelHandlerMetrics for the handler, or None if not found.
        """
        return self.handler_metrics.get(handler_id)

    def get_category_count(self, category: EnumMessageCategory) -> int:
        """
        Get dispatch count for a specific category.

        Args:
            category: The message category.

        Returns:
            Number of dispatches for this category.
        """
        category_key = category.value.lower()
        return self.category_metrics.get(category_key, 0)

    def to_dict(self) -> dict[str, object]:
        """
        Convert to dictionary with computed properties included.

        Returns:
            Dictionary with all metrics including computed properties.
        """
        return {
            "total_dispatches": self.total_dispatches,
            "successful_dispatches": self.successful_dispatches,
            "failed_dispatches": self.failed_dispatches,
            "no_handler_count": self.no_handler_count,
            "category_mismatch_count": self.category_mismatch_count,
            "handler_execution_count": self.handler_execution_count,
            "handler_error_count": self.handler_error_count,
            "routes_matched_count": self.routes_matched_count,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "total_latency_ms": self.total_latency_ms,
            "latency_histogram": self.latency_histogram,
            "category_metrics": self.category_metrics,
            "handler_metrics": {
                handler_id: metrics.to_dict()
                for handler_id, metrics in self.handler_metrics.items()
            },
        }

    @classmethod
    def create_empty(cls) -> "ModelDispatchMetrics":
        """
        Create a new empty metrics instance.

        Returns:
            New ModelDispatchMetrics with all counters at zero.
        """
        return cls()


__all__ = ["ModelDispatchMetrics", "LATENCY_HISTOGRAM_BUCKETS"]
