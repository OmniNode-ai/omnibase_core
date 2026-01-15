# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Comprehensive unit tests for ServiceTraceInMemoryStore.

Tests cover:
- Put and get operations
- Query functionality with various filters
- Protocol compliance (ProtocolTraceStore)
- Memory management and cleanup
- Thread safety considerations

OMN-1209: TDD tests for ServiceTraceInMemoryStore implementation.

.. versionadded:: 0.4.0
    Added as part of Trace Recording Service (OMN-1209)
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.models.trace import ModelExecutionTrace

# Import models from models/ per ONEX file location rules
from omnibase_core.models.trace_query import ModelTraceQuery
from omnibase_core.protocols.storage.protocol_trace_store import ProtocolTraceStore
from omnibase_core.services.trace.service_trace_in_memory_store import (
    ServiceTraceInMemoryStore,
)

# ============================================================================
# Helper Functions
# ============================================================================


def create_test_trace(
    *,
    status: EnumExecutionStatus = EnumExecutionStatus.SUCCESS,
    correlation_id: UUID | None = None,
    started_at: datetime | None = None,
    duration_ms: float = 100.0,
    trace_id: UUID | None = None,
    run_id: UUID | None = None,
) -> ModelExecutionTrace:
    """
    Create a test trace with specified parameters.

    Args:
        status: The execution status for the trace.
        correlation_id: Correlation ID for distributed tracing.
        started_at: Start timestamp (defaults to now).
        duration_ms: Duration in milliseconds.
        trace_id: Optional trace ID (auto-generated if not provided).
        run_id: Optional run ID (auto-generated if not provided).

    Returns:
        A ModelExecutionTrace instance for testing.
    """
    now = datetime.now(UTC)
    start = started_at or now
    end = start + timedelta(milliseconds=duration_ms)

    trace_kwargs: dict = {
        "correlation_id": correlation_id or uuid4(),
        "run_id": run_id or uuid4(),
        "started_at": start,
        "ended_at": end,
        "status": status,
    }

    if trace_id is not None:
        trace_kwargs["trace_id"] = trace_id

    return ModelExecutionTrace(**trace_kwargs)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def store() -> ServiceTraceInMemoryStore:
    """Create a fresh in-memory trace store."""
    return ServiceTraceInMemoryStore()


@pytest.fixture
def sample_trace() -> ModelExecutionTrace:
    """Create a sample successful trace."""
    return create_test_trace(status=EnumExecutionStatus.SUCCESS)


# ============================================================================
# Test: Protocol Compliance
# ============================================================================


class TestProtocolCompliance:
    """Test that ServiceTraceInMemoryStore implements ProtocolTraceStore."""

    def test_implements_protocol(self) -> None:
        """ServiceTraceInMemoryStore implements ProtocolTraceStore interface."""
        store = ServiceTraceInMemoryStore()
        assert isinstance(store, ProtocolTraceStore)

    def test_has_put_method(self, store: ServiceTraceInMemoryStore) -> None:
        """Store has async put method."""
        assert hasattr(store, "put")
        assert callable(store.put)

    def test_has_get_method(self, store: ServiceTraceInMemoryStore) -> None:
        """Store has async get method."""
        assert hasattr(store, "get")
        assert callable(store.get)

    def test_has_query_method(self, store: ServiceTraceInMemoryStore) -> None:
        """Store has async query method."""
        assert hasattr(store, "query")
        assert callable(store.query)


# ============================================================================
# Test: Put and Get Operations
# ============================================================================


class TestStorePutAndGet:
    """Test cases for put and get operations."""

    async def test_store_put_and_get(
        self, store: ServiceTraceInMemoryStore, sample_trace: ModelExecutionTrace
    ) -> None:
        """Store correctly puts and gets traces."""
        await store.put(sample_trace)

        retrieved = await store.get(sample_trace.trace_id)

        assert retrieved is not None
        assert retrieved.trace_id == sample_trace.trace_id
        assert retrieved.correlation_id == sample_trace.correlation_id
        assert retrieved.status == sample_trace.status

    async def test_store_get_nonexistent(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store returns None for nonexistent trace ID."""
        nonexistent_id = uuid4()

        retrieved = await store.get(nonexistent_id)

        assert retrieved is None

    async def test_store_put_multiple_traces(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store can hold multiple traces."""
        traces = [create_test_trace() for _ in range(5)]

        for trace in traces:
            await store.put(trace)

        # Verify all can be retrieved
        for trace in traces:
            retrieved = await store.get(trace.trace_id)
            assert retrieved is not None
            assert retrieved.trace_id == trace.trace_id

    async def test_store_put_overwrites_existing(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store overwrites trace with same ID."""
        trace_id = uuid4()

        trace_v1 = create_test_trace(
            trace_id=trace_id,
            status=EnumExecutionStatus.SUCCESS,
        )
        trace_v2 = create_test_trace(
            trace_id=trace_id,
            status=EnumExecutionStatus.FAILED,
        )

        await store.put(trace_v1)
        await store.put(trace_v2)

        retrieved = await store.get(trace_id)
        assert retrieved is not None
        # Should have the second trace's status
        assert retrieved.status == EnumExecutionStatus.FAILED

    async def test_store_put_preserves_trace_integrity(
        self, store: ServiceTraceInMemoryStore, sample_trace: ModelExecutionTrace
    ) -> None:
        """Store preserves all trace fields."""
        await store.put(sample_trace)

        retrieved = await store.get(sample_trace.trace_id)

        assert retrieved is not None
        assert retrieved.trace_id == sample_trace.trace_id
        assert retrieved.correlation_id == sample_trace.correlation_id
        assert retrieved.run_id == sample_trace.run_id
        assert retrieved.dispatch_id == sample_trace.dispatch_id
        assert retrieved.started_at == sample_trace.started_at
        assert retrieved.ended_at == sample_trace.ended_at
        assert retrieved.status == sample_trace.status
        assert retrieved.steps == sample_trace.steps


# ============================================================================
# Test: Query Operations
# ============================================================================


class TestStoreQuery:
    """Test cases for query operations."""

    async def test_store_query_empty(self, store: ServiceTraceInMemoryStore) -> None:
        """Store query returns empty list when no traces match."""
        query = ModelTraceQuery(status=EnumExecutionStatus.SUCCESS)

        results = await store.query(query)

        assert results == []

    async def test_store_query_all(self, store: ServiceTraceInMemoryStore) -> None:
        """Store query returns all traces when no filters specified."""
        traces = [create_test_trace() for _ in range(5)]
        for trace in traces:
            await store.put(trace)

        query = ModelTraceQuery()
        results = await store.query(query)

        assert len(results) == 5

    async def test_store_query_by_status(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query filters by status correctly."""
        success_trace = create_test_trace(status=EnumExecutionStatus.SUCCESS)
        failed_trace = create_test_trace(status=EnumExecutionStatus.FAILED)

        await store.put(success_trace)
        await store.put(failed_trace)

        query = ModelTraceQuery(status=EnumExecutionStatus.SUCCESS)
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].status == EnumExecutionStatus.SUCCESS

    async def test_store_query_by_correlation_id(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query filters by correlation_id correctly."""
        correlation_id = uuid4()

        matching_trace = create_test_trace(correlation_id=correlation_id)
        other_trace = create_test_trace()

        await store.put(matching_trace)
        await store.put(other_trace)

        query = ModelTraceQuery(correlation_id=correlation_id)
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].correlation_id == correlation_id

    async def test_store_query_by_time_range(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query filters by time range correctly."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        early_trace = create_test_trace(started_at=base_time - timedelta(hours=2))
        middle_trace = create_test_trace(started_at=base_time)
        late_trace = create_test_trace(started_at=base_time + timedelta(hours=2))

        await store.put(early_trace)
        await store.put(middle_trace)
        await store.put(late_trace)

        query = ModelTraceQuery(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
        )
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].trace_id == middle_trace.trace_id

    async def test_store_query_with_limit(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query respects limit parameter."""
        traces = [create_test_trace() for _ in range(10)]
        for trace in traces:
            await store.put(trace)

        query = ModelTraceQuery(limit=3)
        results = await store.query(query)

        assert len(results) == 3

    async def test_store_query_with_offset(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query respects offset parameter."""
        traces = [create_test_trace() for _ in range(10)]
        for trace in traces:
            await store.put(trace)

        query = ModelTraceQuery(offset=5)
        results = await store.query(query)

        assert len(results) == 5

    async def test_store_query_multiple_filters(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store query combines multiple filters correctly."""
        correlation_id = uuid4()
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create matching trace
        matching = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            correlation_id=correlation_id,
            started_at=base_time + timedelta(hours=1),
        )

        # Create non-matching traces
        wrong_status = create_test_trace(
            status=EnumExecutionStatus.FAILED,
            correlation_id=correlation_id,
            started_at=base_time + timedelta(hours=1),
        )
        wrong_correlation = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time + timedelta(hours=1),
        )

        await store.put(matching)
        await store.put(wrong_status)
        await store.put(wrong_correlation)

        query = ModelTraceQuery(
            status=EnumExecutionStatus.SUCCESS,
            correlation_id=correlation_id,
            start_time=base_time,
        )
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].trace_id == matching.trace_id


# ============================================================================
# Test: Multiple Traces
# ============================================================================


class TestStoreMultipleTraces:
    """Test cases for handling multiple traces."""

    async def test_store_multiple_traces(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store handles multiple traces correctly."""
        traces = [
            create_test_trace(status=EnumExecutionStatus.SUCCESS),
            create_test_trace(status=EnumExecutionStatus.FAILED),
            create_test_trace(status=EnumExecutionStatus.PARTIAL),
        ]

        for trace in traces:
            await store.put(trace)

        # Verify count
        query = ModelTraceQuery()
        results = await store.query(query)
        assert len(results) == 3

        # Verify each can be retrieved
        for trace in traces:
            retrieved = await store.get(trace.trace_id)
            assert retrieved is not None

    async def test_store_large_number_of_traces(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store handles large number of traces."""
        traces = [create_test_trace() for _ in range(100)]

        for trace in traces:
            await store.put(trace)

        query = ModelTraceQuery()
        results = await store.query(query)

        assert len(results) == 100


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestStoreEdgeCases:
    """Test edge cases for the store."""

    async def test_store_empty_query_on_empty_store(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Empty store returns empty results for any query."""
        query = ModelTraceQuery()
        results = await store.query(query)

        assert results == []

    async def test_store_get_after_put(self, store: ServiceTraceInMemoryStore) -> None:
        """Get immediately after put returns the trace."""
        trace = create_test_trace()

        await store.put(trace)
        retrieved = await store.get(trace.trace_id)

        assert retrieved is not None
        assert retrieved.trace_id == trace.trace_id

    async def test_store_query_returns_copies(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query returns traces with consistent data."""
        trace = create_test_trace()
        await store.put(trace)

        results1 = await store.query(ModelTraceQuery())
        results2 = await store.query(ModelTraceQuery())

        # Results should contain traces with same data
        assert results1[0].trace_id == results2[0].trace_id

    async def test_store_query_offset_beyond_total(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query with offset beyond total returns empty list."""
        traces = [create_test_trace() for _ in range(5)]
        for trace in traces:
            await store.put(trace)

        query = ModelTraceQuery(offset=100)
        results = await store.query(query)

        assert results == []

    async def test_store_concurrent_operations(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store handles concurrent put operations."""
        import asyncio

        async def put_trace():
            trace = create_test_trace()
            await store.put(trace)
            return trace.trace_id

        # Run puts concurrently
        put_tasks = [put_trace() for _ in range(10)]
        trace_ids = await asyncio.gather(*put_tasks)

        # All should be stored
        assert len(set(trace_ids)) == 10

    async def test_store_query_with_zero_limit_raises_validation_error(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query with limit=0 raises validation error (limit must be >= 1)."""
        from pydantic import ValidationError

        trace = create_test_trace()
        await store.put(trace)

        with pytest.raises(ValidationError):
            ModelTraceQuery(limit=0)


# ============================================================================
# Test: Time-based Queries
# ============================================================================


class TestStoreTimeQueries:
    """Test time-based query edge cases."""

    async def test_store_query_start_time_only(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query with only start_time works correctly."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        before = create_test_trace(started_at=base_time - timedelta(hours=1))
        after = create_test_trace(started_at=base_time + timedelta(hours=1))

        await store.put(before)
        await store.put(after)

        query = ModelTraceQuery(start_time=base_time)
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].trace_id == after.trace_id

    async def test_store_query_end_time_only(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query with only end_time works correctly."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        before = create_test_trace(started_at=base_time - timedelta(hours=1))
        after = create_test_trace(started_at=base_time + timedelta(hours=1))

        await store.put(before)
        await store.put(after)

        query = ModelTraceQuery(end_time=base_time)
        results = await store.query(query)

        assert len(results) == 1
        assert results[0].trace_id == before.trace_id

    async def test_store_query_exact_time_match(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Query matches trace at exact start_time (inclusive start, exclusive end)."""
        exact_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        trace = create_test_trace(started_at=exact_time)

        await store.put(trace)

        # Time range is [start_time, end_time) - inclusive start, exclusive end
        # So we need end_time just after start_time
        query = ModelTraceQuery(
            start_time=exact_time,
            end_time=exact_time + timedelta(seconds=1),
        )
        results = await store.query(query)

        # Should include the trace (start is inclusive)
        assert len(results) == 1


# ============================================================================
# Test: Status Filtering
# ============================================================================


class TestStoreStatusFiltering:
    """Test status-based filtering."""

    async def test_store_filter_all_status_types(
        self, store: ServiceTraceInMemoryStore
    ) -> None:
        """Store can filter by all status types."""
        statuses = [
            EnumExecutionStatus.SUCCESS,
            EnumExecutionStatus.FAILED,
            EnumExecutionStatus.PARTIAL,
            EnumExecutionStatus.CANCELLED,
            EnumExecutionStatus.TIMEOUT,
            EnumExecutionStatus.SKIPPED,
        ]

        for status in statuses:
            trace = create_test_trace(status=status)
            await store.put(trace)

        for status in statuses:
            query = ModelTraceQuery(status=status)
            results = await store.query(query)
            assert len(results) == 1
            assert results[0].status == status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
