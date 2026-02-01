"""
Handler Metrics Model.

Per-handler metrics for dispatch engine observability. Tracks execution counts,
error rates, and latency statistics for individual handlers.

Design Pattern:
    ModelHandlerMetrics is a mutable data model that accumulates metrics during
    dispatch engine operation. Unlike most ONEX models, it is NOT frozen because
    metrics need to be updated in real-time during dispatch operations.

    For thread-safety in production, the dispatch engine maintains its own
    synchronization when updating these metrics.

Thread Safety:
    This model is NOT thread-safe on its own. The MessageDispatchEngine provides
    thread-safety guarantees during metrics collection.

Example:
    >>> from omnibase_core.models.dispatch import ModelHandlerMetrics
    >>>
    >>> metrics = ModelHandlerMetrics(handler_id="user-event-handler")
    >>> metrics = metrics.record_execution(duration_ms=45.2, success=True)
    >>> print(f"Success rate: {metrics.success_rate:.1%}")

See Also:
    omnibase_core.models.dispatch.ModelDispatchMetrics: Aggregate dispatch metrics
    omnibase_core.runtime.MessageDispatchEngine: Uses these for observability
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelHandlerMetrics(BaseModel):
    """
    Metrics for a single handler in the dispatch engine.

    Tracks execution statistics including counts, error rates, and latency
    for observability and performance monitoring.

    Attributes:
        handler_id: The handler's unique identifier.
        execution_count: Total number of times this handler was executed.
        success_count: Number of successful executions.
        error_count: Number of failed executions.
        total_latency_ms: Cumulative latency across all executions.
        min_latency_ms: Minimum observed latency.
        max_latency_ms: Maximum observed latency.
        last_error_message: Most recent error message (if any).
        last_execution_topic: Topic of the most recent execution.

    Example:
        >>> metrics = ModelHandlerMetrics(handler_id="my-handler")
        >>> metrics = metrics.record_execution(duration_ms=50.0, success=True)
        >>> metrics.avg_latency_ms
        50.0
    """

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        validate_assignment=True,
    )

    # ---- Handler Identity ----
    handler_id: str = Field(
        ...,
        description="The handler's unique identifier.",
        min_length=1,
    )

    # ---- Execution Counts ----
    execution_count: int = Field(
        default=0,
        description="Total number of times this handler was executed.",
        ge=0,
    )
    success_count: int = Field(
        default=0,
        description="Number of successful executions.",
        ge=0,
    )
    error_count: int = Field(
        default=0,
        description="Number of failed executions.",
        ge=0,
    )

    # ---- Latency Metrics ----
    total_latency_ms: float = Field(
        default=0.0,
        description="Cumulative latency across all executions in milliseconds.",
        ge=0,
    )
    min_latency_ms: float | None = Field(
        default=None,
        description="Minimum observed latency in milliseconds.",
    )
    max_latency_ms: float | None = Field(
        default=None,
        description="Maximum observed latency in milliseconds.",
    )

    # ---- Last Execution Info ----
    last_error_message: str | None = Field(
        default=None,
        description="Most recent error message (if any).",
    )
    last_execution_topic: str | None = Field(
        default=None,
        description="Topic of the most recent execution.",
    )

    @property
    def avg_latency_ms(self) -> float:
        """
        Calculate average latency across all executions.

        Returns:
            Average latency in milliseconds, or 0.0 if no executions.

        Example:
            >>> metrics = ModelHandlerMetrics(
            ...     handler_id="test",
            ...     execution_count=10,
            ...     total_latency_ms=500.0,
            ... )
            >>> metrics.avg_latency_ms
            50.0
        """
        if self.execution_count == 0:
            return 0.0
        return self.total_latency_ms / self.execution_count

    @property
    def success_rate(self) -> float:
        """
        Calculate success rate as a fraction (0.0 to 1.0).

        Returns:
            Success rate as a decimal, or 1.0 if no executions.

        Example:
            >>> metrics = ModelHandlerMetrics(
            ...     handler_id="test",
            ...     execution_count=100,
            ...     success_count=95,
            ...     error_count=5,
            ... )
            >>> metrics.success_rate
            0.95
        """
        if self.execution_count == 0:
            return 1.0
        return self.success_count / self.execution_count

    @property
    def error_rate(self) -> float:
        """
        Calculate error rate as a fraction (0.0 to 1.0).

        Returns:
            Error rate as a decimal, or 0.0 if no executions.

        Example:
            >>> metrics = ModelHandlerMetrics(
            ...     handler_id="test",
            ...     execution_count=100,
            ...     error_count=5,
            ... )
            >>> metrics.error_rate
            0.05
        """
        if self.execution_count == 0:
            return 0.0
        return self.error_count / self.execution_count

    def record_execution(
        self,
        duration_ms: float,
        success: bool,
        topic: str | None = None,
        error_message: str | None = None,
    ) -> "ModelHandlerMetrics":
        """
        Record an execution and return updated metrics.

        Creates a new ModelHandlerMetrics instance with updated statistics.

        Args:
            duration_ms: Execution duration in milliseconds.
            success: Whether the execution was successful.
            topic: Optional topic the message was from.
            error_message: Optional error message if execution failed.

        Returns:
            New ModelHandlerMetrics with updated statistics.

        Example:
            >>> metrics = ModelHandlerMetrics(handler_id="test")
            >>> metrics = metrics.record_execution(
            ...     duration_ms=45.0,
            ...     success=True,
            ...     topic="user.events.v1",
            ... )
            >>> metrics.execution_count
            1
        """
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

        return ModelHandlerMetrics(
            handler_id=self.handler_id,
            execution_count=self.execution_count + 1,
            success_count=self.success_count + (1 if success else 0),
            error_count=self.error_count + (0 if success else 1),
            total_latency_ms=self.total_latency_ms + duration_ms,
            min_latency_ms=new_min,
            max_latency_ms=new_max,
            last_error_message=error_message
            if not success
            else self.last_error_message,
            last_execution_topic=topic if topic else self.last_execution_topic,
        )

    def to_dict(self) -> dict[str, float | int | str | None]:
        """
        Convert to dictionary with computed properties included.

        Returns:
            Dictionary with all metrics including computed properties.
        """
        return {
            "handler_id": self.handler_id,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms,
            "max_latency_ms": self.max_latency_ms,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "last_error_message": self.last_error_message,
            "last_execution_topic": self.last_execution_topic,
        }


__all__ = ["ModelHandlerMetrics"]
