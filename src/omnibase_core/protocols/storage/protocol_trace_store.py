"""
Protocol definition for trace storage backends.

Defines the ProtocolTraceStore interface that all trace storage implementations
must satisfy. This enables pluggable backends (in-memory, PostgreSQL, etc.)
while maintaining a consistent API.

Example:
    >>> from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore
    >>> from omnibase_core.services.trace.service_trace_in_memory_store import ServiceTraceInMemoryStore
    >>>
    >>> # ServiceTraceInMemoryStore implements ProtocolTraceStore
    >>> store: ProtocolTraceStore = ServiceTraceInMemoryStore()
    >>> # Now use store.put(), store.get(), etc.

See Also:
    - :class:`~omnibase_core.services.trace.service_trace_in_memory_store.ServiceTraceInMemoryStore`:
      In-memory implementation
    - :class:`~omnibase_core.models.trace.ModelExecutionTrace`:
      The trace model being stored

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.models.trace import ModelExecutionTrace
    from omnibase_core.models.trace_query import ModelTraceQuery, ModelTraceSummary


@runtime_checkable
class ProtocolTraceStore(Protocol):
    """
    Protocol defining the interface for trace storage backends.

    All trace storage implementations (in-memory, PostgreSQL, etc.) must
    implement this protocol to ensure consistent behavior across backends.

    The protocol defines four core operations:
        - ``put``: Store a trace
        - ``get``: Retrieve a trace by ID
        - ``query``: Search traces with filters
        - ``summary``: Get aggregate statistics

    Thread Safety:
        Thread safety depends on the specific implementation. See individual
        implementation classes for their thread safety guarantees.

    Example:
        >>> class MyCustomStore:
        ...     async def put(self, trace: ModelExecutionTrace) -> None:
        ...         # Store trace in custom backend
        ...         pass
        ...
        ...     async def get(self, trace_id: UUID) -> ModelExecutionTrace | None:
        ...         # Retrieve trace from custom backend
        ...         return None
        ...
        ...     async def query(
        ...         self, filters: ModelTraceQuery
        ...     ) -> list[ModelExecutionTrace]:
        ...         # Query traces with filters
        ...         return []
        ...
        ...     async def summary(self, filters: ModelTraceQuery) -> ModelTraceSummary:
        ...         # Compute summary statistics
        ...         pass

    .. versionadded:: 0.4.0
        Added as part of Trace Recording Service (OMN-1209)
    """

    async def put(self, trace: "ModelExecutionTrace") -> None:
        """
        Store an execution trace.

        If a trace with the same trace_id already exists, it will be
        overwritten (upsert semantics).

        Args:
            trace: The execution trace to store.

        Raises:
            Implementation-specific exceptions may be raised for storage errors.

        Example:
            >>> from datetime import datetime, UTC
            >>> from uuid import uuid4
            >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
            >>> from omnibase_core.models.trace import ModelExecutionTrace
            >>>
            >>> trace = ModelExecutionTrace(
            ...     correlation_id=uuid4(),
            ...     run_id=uuid4(),
            ...     started_at=datetime.now(UTC),
            ...     ended_at=datetime.now(UTC),
            ...     status=EnumExecutionStatus.SUCCESS,
            ... )
            >>> await store.put(trace)
        """
        ...

    async def get(self, trace_id: UUID) -> "ModelExecutionTrace | None":
        """
        Retrieve a trace by its unique identifier.

        Args:
            trace_id: The UUID of the trace to retrieve.

        Returns:
            The trace if found, None otherwise.

        Example:
            >>> trace = await store.get(trace_id)
            >>> if trace:
            ...     print(f"Found trace: {trace.status}")
            ... else:
            ...     print("Trace not found")
        """
        ...

    async def query(self, filters: "ModelTraceQuery") -> "list[ModelExecutionTrace]":
        """
        Query traces matching the specified filters.

        Filters are applied conjunctively (AND). Only traces matching ALL
        specified filter criteria are returned.

        Args:
            filters: Query filters including status, correlation_id, time range,
                limit, and offset for pagination.

        Returns:
            List of traces matching all filter criteria, ordered by started_at
            descending (newest first). The list length is bounded by filters.limit.

        Example:
            >>> from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
            >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
            >>>
            >>> query = ModelTraceQuery(
            ...     status=EnumExecutionStatus.FAILED,
            ...     limit=10,
            ... )
            >>> failed_traces = await store.query(query)
        """
        ...

    async def summary(self, filters: "ModelTraceQuery") -> "ModelTraceSummary":
        """
        Compute aggregate statistics for traces matching the filters.

        Calculates counts, success rates, and duration percentiles across
        all traces matching the filter criteria.

        Args:
            filters: Query filters to scope the summary computation.
                The limit and offset fields are ignored for summaries.

        Returns:
            Summary statistics including counts, success rate, and duration
            percentiles (p50, p95, p99).

        Example:
            >>> from datetime import datetime, UTC, timedelta
            >>> from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
            >>>
            >>> # Get summary for last 24 hours
            >>> now = datetime.now(UTC)
            >>> query = ModelTraceQuery(
            ...     start_time=now - timedelta(hours=24),
            ...     end_time=now,
            ... )
            >>> summary = await store.summary(query)
            >>> print(f"Success rate: {summary.success_rate:.1%}")
        """
        ...


__all__ = ["ProtocolTraceStore"]
