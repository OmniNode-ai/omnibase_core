"""
Service for recording and querying execution traces.

ServiceTraceRecording provides a high-level API for storing and retrieving
execution traces. It wraps a ProtocolTraceStore backend, enabling pluggable
storage while providing a consistent interface.

Thread Safety:
    Thread safety depends on the underlying ProtocolTraceStore implementation.
    When using ServiceTraceInMemoryStore, the service is NOT thread-safe.
    See ServiceTraceInMemoryStore documentation for thread safety guidelines.

Example:
    >>> from omnibase_core.services.trace.service_trace_recording import (
    ...     ServiceTraceRecording,
    ... )
    >>> from omnibase_core.services.trace.service_trace_in_memory_store import ServiceTraceInMemoryStore
    >>> from omnibase_core.models.trace import ModelExecutionTrace
    >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>>
    >>> # Create service with in-memory backend
    >>> store = ServiceTraceInMemoryStore()
    >>> service = ServiceTraceRecording(store)
    >>>
    >>> # Record a trace
    >>> trace = ModelExecutionTrace(
    ...     correlation_id=uuid4(),
    ...     run_id=uuid4(),
    ...     started_at=datetime.now(UTC),
    ...     ended_at=datetime.now(UTC),
    ...     status=EnumExecutionStatus.SUCCESS,
    ... )
    >>> trace_id = await service.record_trace(trace)
    >>>
    >>> # Retrieve the trace
    >>> retrieved = await service.get_trace(trace_id)

See Also:
    - :class:`~omnibase_core.protocols.storage.protocol_trace_store.ProtocolTraceStore`:
      The storage backend protocol
    - :class:`~omnibase_core.services.trace.service_trace_in_memory_store.ServiceTraceInMemoryStore`:
      In-memory backend implementation
    - :class:`~omnibase_core.models.trace.ModelExecutionTrace`:
      The trace model

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from datetime import datetime
from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.trace import ModelExecutionTrace
from omnibase_core.models.trace_query import ModelTraceQuery, ModelTraceSummary
from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore


class ServiceTraceRecording:
    """
    High-level service for recording and querying execution traces.

    Wraps a ProtocolTraceStore backend to provide a consistent API for
    trace operations. Supports any backend implementing ProtocolTraceStore.

    Attributes:
        _store: The underlying trace storage backend.

    Thread Safety:
        Thread safety is determined by the underlying store implementation.
        See store-specific documentation for details.

    Example:
        >>> from omnibase_core.services.trace.service_trace_recording import (
        ...     ServiceTraceRecording,
        ... )
        >>> from omnibase_core.services.trace.service_trace_in_memory_store import ServiceTraceInMemoryStore
        >>>
        >>> store = ServiceTraceInMemoryStore()
        >>> service = ServiceTraceRecording(store)
        >>>
        >>> # Record traces
        >>> trace_id = await service.record_trace(trace)
        >>>
        >>> # Query traces
        >>> query = ModelTraceQuery(status=EnumExecutionStatus.FAILED)
        >>> failed = await service.query_traces(query)
        >>>
        >>> # Get summary statistics
        >>> summary = await service.get_trace_summary(start_time, end_time)

    .. versionadded:: 0.4.0
        Added as part of Trace Recording Service (OMN-1209)
    """

    def __init__(self, store: ProtocolTraceStore) -> None:
        """
        Initialize the trace recording service.

        Args:
            store: The storage backend to use for trace persistence.
                Must implement ProtocolTraceStore protocol.

        Example:
            >>> from omnibase_core.services.trace.service_trace_in_memory_store import (
            ...     ServiceTraceInMemoryStore,
            ... )
            >>> store = ServiceTraceInMemoryStore()
            >>> service = ServiceTraceRecording(store)
        """
        self._store = store

    async def record_trace(self, trace: ModelExecutionTrace) -> UUID:
        """
        Record an execution trace.

        Stores the trace in the backend and returns its unique identifier.
        If a trace with the same trace_id already exists, it will be
        overwritten (upsert semantics).

        Args:
            trace: The execution trace to record.

        Returns:
            The trace_id of the recorded trace.

        Example:
            >>> from datetime import datetime, UTC
            >>> from uuid import uuid4
            >>> from omnibase_core.models.trace import ModelExecutionTrace
            >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
            >>>
            >>> trace = ModelExecutionTrace(
            ...     correlation_id=uuid4(),
            ...     run_id=uuid4(),
            ...     started_at=datetime.now(UTC),
            ...     ended_at=datetime.now(UTC),
            ...     status=EnumExecutionStatus.SUCCESS,
            ... )
            >>> trace_id = await service.record_trace(trace)
            >>> print(f"Recorded trace: {trace_id}")
        """
        await self._store.put(trace)
        return trace.trace_id

    async def get_trace(self, trace_id: UUID) -> ModelExecutionTrace | None:
        """
        Retrieve a trace by its unique identifier.

        Args:
            trace_id: The UUID of the trace to retrieve.

        Returns:
            The trace if found, None otherwise.

        Example:
            >>> trace = await service.get_trace(trace_id)
            >>> if trace:
            ...     print(f"Trace status: {trace.status}")
            ...     print(f"Duration: {trace.get_duration_ms():.1f}ms")
            ... else:
            ...     print("Trace not found")
        """
        return await self._store.get(trace_id)

    async def query_traces(self, query: ModelTraceQuery) -> list[ModelExecutionTrace]:
        """
        Query traces matching the specified filters.

        Filters are applied conjunctively (AND). Only traces matching ALL
        specified filter criteria are returned.

        Args:
            query: Query filters including status, correlation_id, time range,
                limit, and offset for pagination.

        Returns:
            List of traces matching all filter criteria, ordered by started_at
            descending (newest first).

        Example:
            >>> from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
            >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
            >>> from datetime import datetime, UTC, timedelta
            >>>
            >>> # Query recent failures
            >>> now = datetime.now(UTC)
            >>> query = ModelTraceQuery(
            ...     status=EnumExecutionStatus.FAILED,
            ...     start_time=now - timedelta(hours=1),
            ...     limit=20,
            ... )
            >>> failed_traces = await service.query_traces(query)
            >>> print(f"Found {len(failed_traces)} failed traces")
        """
        return await self._store.query(query)

    async def get_trace_summary(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> ModelTraceSummary:
        """
        Get aggregate statistics for traces in the specified time range.

        Calculates counts, success rates, and duration percentiles across
        all traces with started_at within [start_time, end_time).

        Args:
            start_time: Start of the time range (inclusive).
            end_time: End of the time range (exclusive).

        Returns:
            Summary statistics including counts, success rate, and duration
            percentiles (p50, p95, p99).

        Raises:
            ModelOnexError: If end_time is before start_time (with VALIDATION_ERROR code).

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>>
            >>> # Get summary for last 24 hours
            >>> now = datetime.now(UTC)
            >>> summary = await service.get_trace_summary(
            ...     start_time=now - timedelta(hours=24),
            ...     end_time=now,
            ... )
            >>> print(f"Total traces: {summary.total_traces}")
            >>> print(f"Success rate: {summary.success_rate:.1%}")
            >>> print(f"P95 latency: {summary.p95_duration_ms:.1f}ms")
            >>>
            >>> # Check SLA compliance
            >>> if summary.meets_sla(min_success_rate=0.99, max_p99_ms=500):
            ...     print("SLA met!")
        """
        if end_time < start_time:
            raise ModelOnexError(
                message=f"end_time ({end_time}) cannot be before start_time ({start_time})",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        query = ModelTraceQuery(
            start_time=start_time,
            end_time=end_time,
        )
        return await self._store.summary(query)

    async def query_by_correlation(
        self,
        correlation_id: UUID,
        limit: int = 100,
    ) -> list[ModelExecutionTrace]:
        """
        Query all traces with a specific correlation ID.

        Convenience method for distributed tracing scenarios where you need
        to find all traces in a correlated execution chain.

        Args:
            correlation_id: The correlation ID to search for.
            limit: Maximum number of traces to return (default 100).

        Returns:
            List of traces with the specified correlation ID, ordered by
            started_at descending (newest first).

        Example:
            >>> # Find all traces for a distributed operation
            >>> traces = await service.query_by_correlation(correlation_id)
            >>> print(f"Found {len(traces)} related traces")
            >>> for trace in traces:
            ...     print(f"  {trace.trace_id}: {trace.status}")
        """
        query = ModelTraceQuery(
            correlation_id=correlation_id,
            limit=limit,
        )
        return await self._store.query(query)

    async def has_failures_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        """
        Check if there are any failed traces in the time range.

        This method fetches summary statistics for the time range and checks
        if any failures exist. For scenarios requiring only a boolean check
        without full statistics, consider implementing a dedicated exists
        query on the underlying store for better performance with large
        trace volumes.

        Args:
            start_time: Start of the time range (inclusive).
            end_time: End of the time range (exclusive).

        Returns:
            True if at least one failed trace exists in the range,
            False otherwise.

        Raises:
            ModelOnexError: If end_time is before start_time (from get_trace_summary).

        Note:
            This method computes full summary statistics internally. If you
            need both failure detection and statistics, call get_trace_summary
            directly to avoid redundant computation.

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>>
            >>> now = datetime.now(UTC)
            >>> if await service.has_failures_in_range(
            ...     now - timedelta(hours=1), now
            ... ):
            ...     print("WARNING: Failures detected in last hour!")
        """
        summary = await self.get_trace_summary(start_time, end_time)
        return summary.failure_count > 0


__all__ = ["ServiceTraceRecording"]
