"""
Query filter model for trace retrieval.

Defines ModelTraceQuery for filtering traces by status, correlation ID,
time range, and pagination. Used by ProtocolTraceStore.query() and
ProtocolTraceStore.summary() methods.

Example:
    >>> from datetime import datetime, UTC, timedelta
    >>> from uuid import uuid4
    >>> from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
    >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
    >>>
    >>> # Query for failed traces in the last hour
    >>> now = datetime.now(UTC)
    >>> query = ModelTraceQuery(
    ...     status=EnumExecutionStatus.FAILED,
    ...     start_time=now - timedelta(hours=1),
    ...     end_time=now,
    ...     limit=50,
    ... )

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_trace_store.ProtocolTraceStore`:
      Protocol using this query model
    - :class:`~omnibase_core.enums.enum_execution_status.EnumExecutionStatus`:
      Status values for filtering

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus


class ModelTraceQuery(BaseModel):
    """
    Query filters for trace retrieval and aggregation.

    All filter fields are optional. When multiple filters are specified,
    they are applied conjunctively (AND logic). Unspecified filters match
    all traces.

    Attributes:
        status: Filter by execution status (SUCCESS, FAILED, PARTIAL, etc.).
            If None, matches all statuses.
        correlation_id: Filter by correlation ID for distributed tracing.
            If None, matches all correlation IDs.
        start_time: Include only traces that started at or after this time.
            If None, no lower time bound is applied.
        end_time: Include only traces that started before this time.
            If None, no upper time bound is applied.
        limit: Maximum number of traces to return (1-1000, default 100).
        offset: Number of traces to skip for pagination (default 0).

    Example:
        >>> from datetime import datetime, UTC, timedelta
        >>> from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
        >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
        >>>
        >>> # Basic query - get failed traces
        >>> query = ModelTraceQuery(status=EnumExecutionStatus.FAILED)
        >>>
        >>> # Time-bounded query
        >>> now = datetime.now(UTC)
        >>> query = ModelTraceQuery(
        ...     start_time=now - timedelta(hours=24),
        ...     end_time=now,
        ... )
        >>>
        >>> # Paginated query
        >>> query = ModelTraceQuery(limit=50, offset=100)

    .. versionadded:: 0.4.0
        Added as part of Trace Recording Service (OMN-1209)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
        use_enum_values=False,
    )

    # === Filter Fields ===

    status: EnumExecutionStatus | None = Field(
        default=None,
        description="Filter by execution status (SUCCESS, FAILED, etc.)",
    )

    correlation_id: UUID | None = Field(
        default=None,
        description="Filter by correlation ID for distributed tracing",
    )

    start_time: datetime | None = Field(
        default=None,
        description="Include only traces starting at or after this time",
    )

    end_time: datetime | None = Field(
        default=None,
        description="Include only traces starting before this time",
    )

    # === Pagination Fields ===

    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of traces to return (1-1000)",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of traces to skip for pagination",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_time_range(self) -> "ModelTraceQuery":
        """Validate that end_time is not before start_time."""
        if self.end_time is not None and self.start_time is not None:
            if self.end_time < self.start_time:
                # error-ok: Pydantic model_validator requires ValueError
                raise ValueError(
                    f"end_time ({self.end_time}) cannot be before "
                    f"start_time ({self.start_time})"
                )
        return self

    # === Utility Methods ===

    def has_time_filter(self) -> bool:
        """
        Check if any time-based filter is specified.

        Returns:
            True if start_time or end_time is set.
        """
        return self.start_time is not None or self.end_time is not None

    def has_filters(self) -> bool:
        """
        Check if any filter (non-pagination) is specified.

        Returns:
            True if any of status, correlation_id, start_time, or end_time is set.
        """
        return any(
            [
                self.status is not None,
                self.correlation_id is not None,
                self.start_time is not None,
                self.end_time is not None,
            ]
        )

    def matches_trace_status(self, status: EnumExecutionStatus) -> bool:
        """
        Check if a trace status matches the filter.

        Args:
            status: The trace status to check.

        Returns:
            True if the status matches or no status filter is set.
        """
        if self.status is None:
            return True
        return status == self.status

    def matches_correlation(self, correlation_id: UUID) -> bool:
        """
        Check if a correlation ID matches the filter.

        Args:
            correlation_id: The correlation ID to check.

        Returns:
            True if the correlation ID matches or no filter is set.
        """
        if self.correlation_id is None:
            return True
        return correlation_id == self.correlation_id

    def matches_time_range(self, started_at: datetime) -> bool:
        """
        Check if a trace start time falls within the filter range.

        Args:
            started_at: The trace start timestamp to check.

        Returns:
            True if the time is within the range or no time filter is set.
        """
        if self.start_time is not None and started_at < self.start_time:
            return False
        if self.end_time is not None and started_at >= self.end_time:
            return False
        return True

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        filters = []
        if self.status is not None:
            filters.append(f"status={self.status.value}")
        if self.correlation_id is not None:
            filters.append(f"correlation_id={self.correlation_id}")
        if self.start_time is not None:
            filters.append(f"start_time>={self.start_time.isoformat()}")
        if self.end_time is not None:
            filters.append(f"end_time<{self.end_time.isoformat()}")
        filters.append(f"limit={self.limit}")
        if self.offset > 0:
            filters.append(f"offset={self.offset}")
        return f"TraceQuery({', '.join(filters)})"


__all__ = ["ModelTraceQuery"]
