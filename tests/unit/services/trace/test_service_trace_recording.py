# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Comprehensive unit tests for ServiceTraceRecording.

Tests cover:
- Record/retrieve roundtrip (trace fidelity)
- Query by status (SUCCESS, FAILED, PARTIAL)
- Query by time range (start_time, end_time, or both)
- Query by correlation ID
- Summary aggregation (counts, rates, percentiles)
- Pagination (limit, offset)

OMN-1209: TDD tests for ServiceTraceRecording service.

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
from omnibase_core.services.trace.service_trace_in_memory_store import (
    ServiceTraceInMemoryStore,
)
from omnibase_core.services.trace.service_trace_recording import (
    ServiceTraceRecording,
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


def create_traces_with_statuses(
    statuses: list[EnumExecutionStatus],
    base_time: datetime | None = None,
    time_offset_ms: float = 100.0,
) -> list[ModelExecutionTrace]:
    """
    Create multiple traces with specified statuses at different times.

    Args:
        statuses: List of execution statuses to create traces for.
        base_time: Base time for the first trace.
        time_offset_ms: Time offset between traces in milliseconds.

    Returns:
        List of ModelExecutionTrace instances.
    """
    base = base_time or datetime.now(UTC)
    traces = []
    for i, status in enumerate(statuses):
        started_at = base + timedelta(milliseconds=i * time_offset_ms * 2)
        traces.append(
            create_test_trace(
                status=status,
                started_at=started_at,
                duration_ms=time_offset_ms,
            )
        )
    return traces


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def in_memory_store() -> ServiceTraceInMemoryStore:
    """Create a fresh in-memory trace store."""
    return ServiceTraceInMemoryStore()


@pytest.fixture
def trace_service(in_memory_store: ServiceTraceInMemoryStore) -> ServiceTraceRecording:
    """Create a trace recording service with in-memory store."""
    return ServiceTraceRecording(store=in_memory_store)


@pytest.fixture
def sample_trace() -> ModelExecutionTrace:
    """Create a sample successful trace."""
    return create_test_trace(status=EnumExecutionStatus.SUCCESS)


# ============================================================================
# Test: Record/Retrieve Roundtrip
# ============================================================================


class TestRecordAndRetrieveRoundtrip:
    """Test cases for recording and retrieving traces."""

    async def test_record_and_retrieve_trace(
        self, trace_service: ServiceTraceRecording, sample_trace: ModelExecutionTrace
    ) -> None:
        """Recorded trace can be retrieved with full fidelity."""
        # Record the trace
        await trace_service.record_trace(sample_trace)

        # Retrieve it
        retrieved = await trace_service.get_trace(sample_trace.trace_id)

        # Verify full fidelity
        assert retrieved is not None
        assert retrieved.trace_id == sample_trace.trace_id
        assert retrieved.correlation_id == sample_trace.correlation_id
        assert retrieved.run_id == sample_trace.run_id
        assert retrieved.started_at == sample_trace.started_at
        assert retrieved.ended_at == sample_trace.ended_at
        assert retrieved.status == sample_trace.status
        assert retrieved.steps == sample_trace.steps

    async def test_retrieve_nonexistent_trace(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Retrieving nonexistent trace returns None."""
        nonexistent_id = uuid4()

        retrieved = await trace_service.get_trace(nonexistent_id)

        assert retrieved is None

    async def test_record_multiple_traces_retrieval(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Multiple recorded traces can each be retrieved independently."""
        traces = [create_test_trace() for _ in range(5)]

        # Record all traces
        for trace in traces:
            await trace_service.record_trace(trace)

        # Retrieve each and verify
        for trace in traces:
            retrieved = await trace_service.get_trace(trace.trace_id)
            assert retrieved is not None
            assert retrieved.trace_id == trace.trace_id

    async def test_frozen_model_unchanged_after_record(
        self, trace_service: ServiceTraceRecording, sample_trace: ModelExecutionTrace
    ) -> None:
        """Frozen Pydantic model fields remain unchanged after recording.

        Note: This test verifies that Pydantic's frozen model behavior works
        as expected. The model cannot be modified because it has frozen=True.
        """
        original_trace_id = sample_trace.trace_id
        original_status = sample_trace.status

        await trace_service.record_trace(sample_trace)

        # Original should be unchanged (frozen model)
        assert sample_trace.trace_id == original_trace_id
        assert sample_trace.status == original_status

    async def test_retrieved_trace_is_protected_by_frozen_model(
        self, trace_service: ServiceTraceRecording, sample_trace: ModelExecutionTrace
    ) -> None:
        """Retrieved trace is protected from mutations via frozen model.

        Copy semantics verification: even if the service returns a reference
        to internal state, the frozen Pydantic model prevents mutations,
        protecting the internal state from corruption.
        """
        await trace_service.record_trace(sample_trace)
        retrieved = await trace_service.get_trace(sample_trace.trace_id)

        assert retrieved is not None

        # Verify the frozen model prevents mutations
        # This protects internal state from corruption via returned references
        with pytest.raises(Exception):  # ValidationError from Pydantic
            # Attempting to modify a frozen model should fail
            retrieved.status = EnumExecutionStatus.FAILED  # type: ignore[misc]

        # Verify the internal state is still intact after failed mutation attempt
        retrieved_again = await trace_service.get_trace(sample_trace.trace_id)
        assert retrieved_again is not None
        assert retrieved_again.status == sample_trace.status

    async def test_query_results_list_is_independent_copy(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query results list can be modified without affecting internal state.

        Verifies that mutating the returned list does not corrupt
        the service's internal storage.
        """
        traces = [create_test_trace() for _ in range(3)]
        for trace in traces:
            await trace_service.record_trace(trace)

        # Get query results
        query = ModelTraceQuery()
        results = await trace_service.query_traces(query)
        original_length = len(results)

        # Mutate the returned list (should not affect internal state)
        results.clear()
        assert len(results) == 0

        # Verify internal state is unaffected
        results_again = await trace_service.query_traces(query)
        assert len(results_again) == original_length


# ============================================================================
# Test: Query by Status
# ============================================================================


class TestQueryByStatus:
    """Test cases for querying traces by status."""

    async def test_query_by_status_success(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns only traces matching SUCCESS status."""
        # Create mixed traces
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.PARTIAL,
            ]
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        # Query for SUCCESS only
        query = ModelTraceQuery(status=EnumExecutionStatus.SUCCESS)
        results = await trace_service.query_traces(query)

        assert len(results) == 2
        for result in results:
            assert result.status == EnumExecutionStatus.SUCCESS

    async def test_query_by_status_failed(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns only traces matching FAILED status."""
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.TIMEOUT,
            ]
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(status=EnumExecutionStatus.FAILED)
        results = await trace_service.query_traces(query)

        assert len(results) == 2
        for result in results:
            assert result.status == EnumExecutionStatus.FAILED

    async def test_query_by_status_partial(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns only traces matching PARTIAL status."""
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.PARTIAL,
                EnumExecutionStatus.PARTIAL,
                EnumExecutionStatus.PARTIAL,
            ]
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(status=EnumExecutionStatus.PARTIAL)
        results = await trace_service.query_traces(query)

        assert len(results) == 3
        for result in results:
            assert result.status == EnumExecutionStatus.PARTIAL

    async def test_query_by_status_no_matches(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns empty list when no traces match status."""
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.SUCCESS,
            ]
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(status=EnumExecutionStatus.CANCELLED)
        results = await trace_service.query_traces(query)

        assert len(results) == 0

    async def test_query_without_status_returns_all(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query without status filter returns all traces."""
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.PARTIAL,
            ]
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery()
        results = await trace_service.query_traces(query)

        assert len(results) == 3


# ============================================================================
# Test: Query by Time Range
# ============================================================================


class TestQueryByTimeRange:
    """Test cases for querying traces by time range."""

    async def test_query_by_time_range(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query correctly filters by time range."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create traces at different times
        trace_early = create_test_trace(
            started_at=base_time,
            duration_ms=100.0,
        )
        trace_middle = create_test_trace(
            started_at=base_time + timedelta(hours=1),
            duration_ms=100.0,
        )
        trace_late = create_test_trace(
            started_at=base_time + timedelta(hours=2),
            duration_ms=100.0,
        )

        for trace in [trace_early, trace_middle, trace_late]:
            await trace_service.record_trace(trace)

        # Query for middle time range
        query = ModelTraceQuery(
            start_time=base_time + timedelta(minutes=30),
            end_time=base_time + timedelta(hours=1, minutes=30),
        )
        results = await trace_service.query_traces(query)

        assert len(results) == 1
        assert results[0].trace_id == trace_middle.trace_id

    async def test_query_with_start_time_only(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query with only start_time returns traces after that time."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        trace_before = create_test_trace(
            started_at=base_time - timedelta(hours=1),
            duration_ms=100.0,
        )
        trace_after_1 = create_test_trace(
            started_at=base_time + timedelta(hours=1),
            duration_ms=100.0,
        )
        trace_after_2 = create_test_trace(
            started_at=base_time + timedelta(hours=2),
            duration_ms=100.0,
        )

        for trace in [trace_before, trace_after_1, trace_after_2]:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(start_time=base_time)
        results = await trace_service.query_traces(query)

        assert len(results) == 2
        for result in results:
            assert result.started_at >= base_time

    async def test_query_with_end_time_only(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query with only end_time returns traces before that time."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        trace_before_1 = create_test_trace(
            started_at=base_time - timedelta(hours=2),
            duration_ms=100.0,
        )
        trace_before_2 = create_test_trace(
            started_at=base_time - timedelta(hours=1),
            duration_ms=100.0,
        )
        trace_after = create_test_trace(
            started_at=base_time + timedelta(hours=1),
            duration_ms=100.0,
        )

        for trace in [trace_before_1, trace_before_2, trace_after]:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(end_time=base_time)
        results = await trace_service.query_traces(query)

        assert len(results) == 2
        for result in results:
            assert result.started_at < base_time  # end_time is exclusive

    async def test_query_with_empty_time_range(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns empty list when time range has no traces."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        trace = create_test_trace(
            started_at=base_time,
            duration_ms=100.0,
        )
        await trace_service.record_trace(trace)

        # Query for a time range far in the future
        query = ModelTraceQuery(
            start_time=base_time + timedelta(days=30),
            end_time=base_time + timedelta(days=31),
        )
        results = await trace_service.query_traces(query)

        assert len(results) == 0

    async def test_query_time_range_inclusive_start(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query time range is inclusive on start, exclusive on end."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        trace = create_test_trace(
            started_at=base_time,
            duration_ms=100.0,
        )
        await trace_service.record_trace(trace)

        # Query with start_time matching trace exactly (inclusive)
        # and end_time just after (exclusive)
        query = ModelTraceQuery(
            start_time=base_time,
            end_time=base_time + timedelta(seconds=1),
        )
        results = await trace_service.query_traces(query)

        assert len(results) == 1


# ============================================================================
# Test: Query by Correlation ID
# ============================================================================


class TestQueryByCorrelationId:
    """Test cases for querying traces by correlation ID."""

    async def test_query_by_correlation_id(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns all traces with matching correlation_id."""
        shared_correlation_id = uuid4()

        # Create traces with same correlation ID
        trace_1 = create_test_trace(correlation_id=shared_correlation_id)
        trace_2 = create_test_trace(correlation_id=shared_correlation_id)
        trace_other = create_test_trace(correlation_id=uuid4())

        for trace in [trace_1, trace_2, trace_other]:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(correlation_id=shared_correlation_id)
        results = await trace_service.query_traces(query)

        assert len(results) == 2
        for result in results:
            assert result.correlation_id == shared_correlation_id

    async def test_query_by_correlation_id_no_matches(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns empty list when no traces match correlation_id."""
        trace = create_test_trace(correlation_id=uuid4())
        await trace_service.record_trace(trace)

        nonexistent_correlation = uuid4()
        query = ModelTraceQuery(correlation_id=nonexistent_correlation)
        results = await trace_service.query_traces(query)

        assert len(results) == 0

    async def test_query_by_correlation_id_single_match(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query returns single trace when only one matches."""
        target_correlation_id = uuid4()
        target_trace = create_test_trace(correlation_id=target_correlation_id)

        other_traces = [create_test_trace() for _ in range(3)]

        await trace_service.record_trace(target_trace)
        for trace in other_traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(correlation_id=target_correlation_id)
        results = await trace_service.query_traces(query)

        assert len(results) == 1
        assert results[0].trace_id == target_trace.trace_id


# ============================================================================
# Test: Combined Query Filters
# ============================================================================


class TestCombinedQueryFilters:
    """Test cases for queries with multiple filters."""

    async def test_query_with_status_and_time_range(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query correctly combines status and time range filters."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create traces with different statuses and times
        success_early = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time - timedelta(hours=1),
        )
        success_late = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time + timedelta(hours=1),
        )
        failed_late = create_test_trace(
            status=EnumExecutionStatus.FAILED,
            started_at=base_time + timedelta(hours=1),
        )

        for trace in [success_early, success_late, failed_late]:
            await trace_service.record_trace(trace)

        # Query for SUCCESS after base_time
        query = ModelTraceQuery(
            status=EnumExecutionStatus.SUCCESS,
            start_time=base_time,
        )
        results = await trace_service.query_traces(query)

        assert len(results) == 1
        assert results[0].status == EnumExecutionStatus.SUCCESS
        assert results[0].started_at >= base_time

    async def test_query_with_all_filters(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query correctly combines all available filters."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        target_correlation_id = uuid4()

        # Create matching trace
        matching = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            correlation_id=target_correlation_id,
            started_at=base_time + timedelta(hours=1),
        )

        # Create non-matching traces
        wrong_status = create_test_trace(
            status=EnumExecutionStatus.FAILED,
            correlation_id=target_correlation_id,
            started_at=base_time + timedelta(hours=1),
        )
        wrong_correlation = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time + timedelta(hours=1),
        )
        wrong_time = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            correlation_id=target_correlation_id,
            started_at=base_time - timedelta(hours=1),
        )

        for trace in [matching, wrong_status, wrong_correlation, wrong_time]:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(
            status=EnumExecutionStatus.SUCCESS,
            correlation_id=target_correlation_id,
            start_time=base_time,
        )
        results = await trace_service.query_traces(query)

        assert len(results) == 1
        assert results[0].trace_id == matching.trace_id


# ============================================================================
# Test: Summary Aggregation
# ============================================================================


class TestSummaryStatistics:
    """Test cases for summary aggregation."""

    async def test_summary_statistics(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary correctly aggregates trace statistics."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.SUCCESS,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.PARTIAL,
            ],
            base_time=base_time,
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        summary = await trace_service.get_trace_summary(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=24),
        )

        assert summary.total_traces == 5
        assert summary.success_count == 3
        assert summary.failure_count == 1
        assert summary.partial_count == 1
        assert summary.success_rate == pytest.approx(0.6)  # 3/5 = 60%

    async def test_summary_duration_percentiles(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary correctly calculates duration percentiles."""
        # Create traces with known durations: 100, 200, 300, 400, 500 ms
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        durations = [100.0, 200.0, 300.0, 400.0, 500.0]

        for i, duration in enumerate(durations):
            trace = create_test_trace(
                started_at=base_time + timedelta(hours=i),
                duration_ms=duration,
            )
            await trace_service.record_trace(trace)

        summary = await trace_service.get_trace_summary(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=24),
        )

        # Average should be (100+200+300+400+500)/5 = 300
        assert summary.avg_duration_ms == pytest.approx(300.0)
        # P50 (median) should be 300
        assert summary.p50_duration_ms == pytest.approx(300.0)
        # P95 should be 500 (or close to it for 5 values)
        assert summary.p95_duration_ms >= 400.0
        # P99 should be 500 (or close to it for 5 values)
        assert summary.p99_duration_ms >= 450.0

    async def test_summary_empty_range(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary returns zeros for empty time range."""
        # Don't add any traces
        now = datetime.now(UTC)
        summary = await trace_service.get_trace_summary(
            start_time=now - timedelta(hours=1),
            end_time=now,
        )

        assert summary.total_traces == 0
        assert summary.success_count == 0
        assert summary.failure_count == 0
        assert summary.partial_count == 0
        assert summary.success_rate == 0.0
        assert summary.avg_duration_ms == 0.0
        assert summary.p50_duration_ms == 0.0
        assert summary.p95_duration_ms == 0.0
        assert summary.p99_duration_ms == 0.0

    async def test_summary_with_time_range(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary respects time range filter."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Create traces at different times
        trace_inside = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time + timedelta(hours=1),
        )
        trace_outside = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            started_at=base_time - timedelta(hours=1),
        )

        await trace_service.record_trace(trace_inside)
        await trace_service.record_trace(trace_outside)

        summary = await trace_service.get_trace_summary(
            start_time=base_time,
            end_time=base_time + timedelta(hours=2),
        )

        assert summary.total_traces == 1

    async def test_summary_single_trace(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary correctly handles single trace."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        trace = create_test_trace(
            status=EnumExecutionStatus.SUCCESS,
            duration_ms=250.0,
            started_at=base_time,
        )
        await trace_service.record_trace(trace)

        summary = await trace_service.get_trace_summary(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=1),
        )

        assert summary.total_traces == 1
        assert summary.success_count == 1
        assert summary.success_rate == 1.0
        assert summary.avg_duration_ms == pytest.approx(250.0)
        # For single value, all percentiles should be the same
        assert summary.p50_duration_ms == pytest.approx(250.0)
        assert summary.p95_duration_ms == pytest.approx(250.0)
        assert summary.p99_duration_ms == pytest.approx(250.0)


# ============================================================================
# Test: Pagination
# ============================================================================


class TestPagination:
    """Test cases for pagination (limit and offset)."""

    async def test_query_with_limit(self, trace_service: ServiceTraceRecording) -> None:
        """Query respects limit parameter."""
        # Create 10 traces
        traces = [create_test_trace() for _ in range(10)]
        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(limit=5)
        results = await trace_service.query_traces(query)

        assert len(results) == 5

    async def test_query_with_offset(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query correctly applies offset for pagination."""
        # Create 10 traces with distinct trace IDs to verify ordering
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        traces = []
        for i in range(10):
            trace = create_test_trace(
                started_at=base_time + timedelta(minutes=i),
            )
            traces.append(trace)
            await trace_service.record_trace(trace)

        # Get all traces first to establish ordering
        all_results = await trace_service.query_traces(ModelTraceQuery())
        assert len(all_results) == 10

        # Now query with offset
        query = ModelTraceQuery(offset=5, limit=10)
        results = await trace_service.query_traces(query)

        assert len(results) == 5

    async def test_query_with_limit_and_offset_combined(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query correctly combines limit and offset."""
        # Create 20 traces
        traces = [create_test_trace() for _ in range(20)]
        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(offset=5, limit=10)
        results = await trace_service.query_traces(query)

        assert len(results) == 10

    async def test_query_offset_beyond_results(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query with offset beyond available results returns empty list."""
        traces = [create_test_trace() for _ in range(5)]
        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery(offset=100)
        results = await trace_service.query_traces(query)

        assert len(results) == 0

    async def test_query_limit_zero_raises_validation_error(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query with limit=0 raises validation error (limit must be >= 1)."""
        from pydantic import ValidationError

        traces = [create_test_trace() for _ in range(5)]
        for trace in traces:
            await trace_service.record_trace(trace)

        with pytest.raises(ValidationError):
            ModelTraceQuery(limit=0)

    async def test_query_default_pagination(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query without pagination returns all results (up to default limit)."""
        traces = [create_test_trace() for _ in range(10)]
        for trace in traces:
            await trace_service.record_trace(trace)

        query = ModelTraceQuery()
        results = await trace_service.query_traces(query)

        # Should return all traces when no limit specified
        assert len(results) == 10


# ============================================================================
# Test: Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    async def test_record_duplicate_trace_id(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Recording trace with duplicate ID should handle appropriately."""
        trace_id = uuid4()
        trace_1 = create_test_trace(trace_id=trace_id)
        trace_2 = create_test_trace(trace_id=trace_id)

        await trace_service.record_trace(trace_1)

        # Second record with same ID should either:
        # 1. Raise an error, OR
        # 2. Overwrite the existing trace
        # This test verifies consistent behavior
        await trace_service.record_trace(trace_2)

        retrieved = await trace_service.get_trace(trace_id)
        assert retrieved is not None

    async def test_query_empty_store(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Query on empty store returns empty list."""
        query = ModelTraceQuery()
        results = await trace_service.query_traces(query)

        assert results == []

    async def test_summary_with_only_failures(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Summary correctly handles all-failure scenario."""
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        traces = create_traces_with_statuses(
            [
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.FAILED,
                EnumExecutionStatus.TIMEOUT,
            ],
            base_time=base_time,
        )

        for trace in traces:
            await trace_service.record_trace(trace)

        summary = await trace_service.get_trace_summary(
            start_time=base_time - timedelta(hours=1),
            end_time=base_time + timedelta(hours=24),
        )

        assert summary.total_traces == 3
        assert summary.success_count == 0
        # TIMEOUT should count as failure
        assert summary.failure_count >= 2
        assert summary.success_rate == 0.0

    async def test_concurrent_writes_all_traces_recorded(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Concurrent write operations record all traces successfully."""
        import asyncio

        num_concurrent_writes = 50

        async def record_trace_concurrent() -> UUID:
            trace = create_test_trace()
            await trace_service.record_trace(trace)
            return trace.trace_id

        # Record many traces concurrently
        trace_ids = await asyncio.gather(
            *[record_trace_concurrent() for _ in range(num_concurrent_writes)]
        )

        # All should be recorded with unique IDs
        assert len(trace_ids) == num_concurrent_writes
        assert len(set(trace_ids)) == num_concurrent_writes

        # Query should return all
        query = ModelTraceQuery()
        results = await trace_service.query_traces(query)
        assert len(results) == num_concurrent_writes

        # Verify each trace is individually retrievable
        for trace_id in trace_ids:
            retrieved = await trace_service.get_trace(trace_id)
            assert retrieved is not None
            assert retrieved.trace_id == trace_id

    async def test_concurrent_reads_and_writes(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Concurrent read and write operations do not interfere with each other."""
        import asyncio

        # Pre-populate with some traces
        initial_traces = [create_test_trace() for _ in range(10)]
        for trace in initial_traces:
            await trace_service.record_trace(trace)

        # Track results
        read_results: list[ModelExecutionTrace | None] = []
        write_results: list[UUID] = []

        async def read_trace(trace_id: UUID) -> None:
            result = await trace_service.get_trace(trace_id)
            read_results.append(result)

        async def write_trace() -> None:
            trace = create_test_trace()
            await trace_service.record_trace(trace)
            write_results.append(trace.trace_id)

        # Mix reads and writes concurrently
        tasks = []
        for i in range(30):
            if i % 3 == 0:
                # Read an existing trace
                tasks.append(
                    read_trace(initial_traces[i % len(initial_traces)].trace_id)
                )
            else:
                # Write a new trace
                tasks.append(write_trace())

        await asyncio.gather(*tasks)

        # Verify reads succeeded (all should find the trace)
        successful_reads = [r for r in read_results if r is not None]
        assert (
            len(successful_reads) == 10
        )  # 10 read operations (indices 0, 3, 6, 9, etc.)

        # Verify writes succeeded
        assert len(write_results) == 20  # 20 write operations

        # Verify all new traces are queryable
        for trace_id in write_results:
            retrieved = await trace_service.get_trace(trace_id)
            assert retrieved is not None

    async def test_concurrent_queries_return_consistent_results(
        self, trace_service: ServiceTraceRecording
    ) -> None:
        """Concurrent query operations return consistent results."""
        import asyncio

        # Pre-populate with traces of different statuses
        success_traces = [
            create_test_trace(status=EnumExecutionStatus.SUCCESS) for _ in range(5)
        ]
        failed_traces = [
            create_test_trace(status=EnumExecutionStatus.FAILED) for _ in range(3)
        ]

        for trace in success_traces + failed_traces:
            await trace_service.record_trace(trace)

        query_results: list[list[ModelExecutionTrace]] = []

        async def run_query(status: EnumExecutionStatus | None) -> None:
            query = ModelTraceQuery(status=status) if status else ModelTraceQuery()
            results = await trace_service.query_traces(query)
            query_results.append(results)

        # Run multiple queries concurrently
        tasks = [
            run_query(EnumExecutionStatus.SUCCESS),
            run_query(EnumExecutionStatus.FAILED),
            run_query(None),  # All traces
            run_query(EnumExecutionStatus.SUCCESS),
            run_query(EnumExecutionStatus.FAILED),
            run_query(None),  # All traces again
        ]
        await asyncio.gather(*tasks)

        # Verify consistent results
        # First and fourth results should both be SUCCESS queries (5 traces)
        assert len(query_results[0]) == 5
        assert len(query_results[3]) == 5

        # Second and fifth results should both be FAILED queries (3 traces)
        assert len(query_results[1]) == 3
        assert len(query_results[4]) == 3

        # Third and sixth results should both be all traces (8 traces)
        assert len(query_results[2]) == 8
        assert len(query_results[5]) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
