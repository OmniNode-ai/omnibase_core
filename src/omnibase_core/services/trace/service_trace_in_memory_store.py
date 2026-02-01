"""
In-memory implementation of ProtocolTraceStore.

Provides a simple dict-based storage backend for execution traces. Suitable
for development, testing, and single-instance deployments. For production
multi-instance deployments, use a persistent backend like PostgreSQL.

Thread Safety:
    ServiceTraceInMemoryStore is NOT thread-safe. The internal dict is not protected
    by locks, and concurrent access from multiple threads may cause data
    corruption or race conditions.

    For thread-safe usage:
    - Use separate ServiceTraceInMemoryStore instances per thread, OR
    - Wrap all operations with threading.Lock

Example:
    >>> from omnibase_core.services.trace.service_trace_in_memory_store import ServiceTraceInMemoryStore
    >>> from omnibase_core.models.trace_query import ModelTraceQuery
    >>> from omnibase_core.models.trace import ModelExecutionTrace
    >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>>
    >>> store = ServiceTraceInMemoryStore()
    >>>
    >>> # Store a trace
    >>> trace = ModelExecutionTrace(
    ...     correlation_id=uuid4(),
    ...     run_id=uuid4(),
    ...     started_at=datetime.now(UTC),
    ...     ended_at=datetime.now(UTC),
    ...     status=EnumExecutionStatus.SUCCESS,
    ... )
    >>> await store.put(trace)
    >>>
    >>> # Retrieve by ID
    >>> retrieved = await store.get(trace.trace_id)
    >>> assert retrieved == trace

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_trace_store.ProtocolTraceStore`:
      The protocol this class implements

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from datetime import UTC, datetime
from uuid import UUID

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.trace import ModelExecutionTrace
from omnibase_core.models.trace_query import ModelTraceQuery, ModelTraceSummary
from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore


class ServiceTraceInMemoryStore:
    """
    In-memory trace storage implementation.

    Stores traces in a Python dict keyed by trace_id. Implements all
    ProtocolTraceStore methods for filtering, pagination, and aggregation.

    Attributes:
        _traces: Internal dict mapping trace_id to ModelExecutionTrace.

    Thread Safety:
        NOT thread-safe. See module docstring for details.

    Memory Considerations:
        All traces are stored in memory. For long-running applications with
        many traces, consider:
        - Implementing a TTL-based eviction policy
        - Using a bounded dict with LRU eviction
        - Switching to a persistent backend

    Example:
        >>> store = ServiceTraceInMemoryStore()
        >>> await store.put(trace)
        >>> print(f"Stored {len(store)} traces")

    .. versionadded:: 0.4.0
        Added as part of Trace Recording Service (OMN-1209)
    """

    def __init__(self) -> None:
        """Initialize an empty in-memory trace store."""
        self._traces: dict[UUID, ModelExecutionTrace] = {}

    def __len__(self) -> int:
        """Return the number of traces in the store."""
        return len(self._traces)

    async def put(self, trace: ModelExecutionTrace) -> None:
        """
        Store an execution trace.

        Uses upsert semantics - if a trace with the same trace_id exists,
        it will be overwritten.

        Args:
            trace: The execution trace to store.
        """
        self._traces[trace.trace_id] = trace

    async def get(self, trace_id: UUID) -> ModelExecutionTrace | None:
        """
        Retrieve a trace by its unique identifier.

        Args:
            trace_id: The UUID of the trace to retrieve.

        Returns:
            The trace if found, None otherwise.
        """
        return self._traces.get(trace_id)

    async def query(self, filters: ModelTraceQuery) -> list[ModelExecutionTrace]:
        """
        Query traces matching the specified filters.

        Filters are applied conjunctively (AND). Results are ordered by
        started_at descending (newest first) and bounded by limit/offset.

        Args:
            filters: Query filters including status, correlation_id, time range,
                limit, and offset for pagination.

        Returns:
            List of matching traces, ordered by started_at descending.
        """
        # Apply filters
        matching_traces = [
            trace
            for trace in self._traces.values()
            if self._matches_filters(trace, filters)
        ]

        # Sort by started_at descending (newest first)
        matching_traces.sort(key=lambda t: t.started_at, reverse=True)

        # Apply pagination
        start_idx = filters.offset
        end_idx = start_idx + filters.limit
        return matching_traces[start_idx:end_idx]

    async def summary(self, filters: ModelTraceQuery) -> ModelTraceSummary:
        """
        Compute aggregate statistics for traces matching the filters.

        The limit and offset fields in filters are ignored for summary
        computation - all matching traces are included.

        Args:
            filters: Query filters to scope the summary computation.

        Returns:
            Summary statistics including counts, success rate, and duration
            percentiles.
        """
        # Get all matching traces (ignore pagination for summary)
        matching_traces = [
            trace
            for trace in self._traces.values()
            if self._matches_filters(trace, filters)
        ]

        # Determine time range
        if matching_traces:
            started_times = [t.started_at for t in matching_traces]
            time_range_start = min(started_times)
            time_range_end = max(t.ended_at for t in matching_traces)
        else:
            # No matching traces - use filter times or now
            now = datetime.now(UTC)
            time_range_start = filters.start_time or now
            time_range_end = filters.end_time or now

        total_traces = len(matching_traces)

        if total_traces == 0:
            # Return empty summary with zero metrics
            return ModelTraceSummary(
                time_range_start=time_range_start,
                time_range_end=time_range_end,
                total_traces=0,
                success_count=0,
                failure_count=0,
                partial_count=0,
                success_rate=0.0,
                avg_duration_ms=0.0,
                p50_duration_ms=0.0,
                p95_duration_ms=0.0,
                p99_duration_ms=0.0,
            )

        # Count by status
        success_count = sum(1 for t in matching_traces if self._is_successful(t.status))
        failure_count = sum(1 for t in matching_traces if self._is_failure(t.status))
        partial_count = sum(1 for t in matching_traces if self._is_partial(t.status))

        # Calculate success rate
        success_rate = success_count / total_traces

        # Calculate duration metrics
        durations = sorted([t.get_duration_ms() for t in matching_traces])
        avg_duration_ms = sum(durations) / len(durations)
        p50_duration_ms = self._percentile(durations, 50)
        p95_duration_ms = self._percentile(durations, 95)
        p99_duration_ms = self._percentile(durations, 99)

        return ModelTraceSummary(
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            total_traces=total_traces,
            success_count=success_count,
            failure_count=failure_count,
            partial_count=partial_count,
            success_rate=success_rate,
            avg_duration_ms=avg_duration_ms,
            p50_duration_ms=p50_duration_ms,
            p95_duration_ms=p95_duration_ms,
            p99_duration_ms=p99_duration_ms,
        )

    def _matches_filters(
        self, trace: ModelExecutionTrace, filters: ModelTraceQuery
    ) -> bool:
        """Check if a trace matches all specified filters."""
        # Check status filter
        if not filters.matches_trace_status(trace.status):
            return False

        # Check correlation_id filter
        if not filters.matches_correlation(trace.correlation_id):
            return False

        # Check time range filter
        if not filters.matches_time_range(trace.started_at):
            return False

        return True

    def _is_successful(self, status: EnumExecutionStatus) -> bool:
        """Check if status indicates success."""
        return EnumExecutionStatus.is_successful(status)

    def _is_failure(self, status: EnumExecutionStatus) -> bool:
        """Check if status indicates failure."""
        return EnumExecutionStatus.is_failure(status)

    def _is_partial(self, status: EnumExecutionStatus) -> bool:
        """Check if status indicates partial completion."""
        return EnumExecutionStatus.is_partial(status)

    def _percentile(self, sorted_values: list[float], percentile: int) -> float:
        """
        Calculate the specified percentile from a sorted list of values.

        Uses linear interpolation between nearest ranks.

        Args:
            sorted_values: A sorted list of float values.
            percentile: The percentile to calculate (0-100).

        Returns:
            The calculated percentile value.
        """
        if not sorted_values:
            return 0.0

        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]

        # Calculate rank (0-indexed position)
        rank = (percentile / 100.0) * (n - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = rank - lower_idx

        # Linear interpolation
        return sorted_values[lower_idx] + fraction * (
            sorted_values[upper_idx] - sorted_values[lower_idx]
        )

    async def clear(self) -> None:
        """
        Remove all traces from the store.

        Useful for testing and cleanup.
        """
        self._traces.clear()

    async def count(self) -> int:
        """
        Get the total number of traces in the store.

        Returns:
            Number of stored traces.
        """
        return len(self._traces)


# Verify protocol compliance at module load time
_store_check: ProtocolTraceStore = ServiceTraceInMemoryStore()

__all__ = ["ServiceTraceInMemoryStore"]
