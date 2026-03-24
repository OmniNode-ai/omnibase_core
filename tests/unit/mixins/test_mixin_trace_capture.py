# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for MixinTraceCapture.

Coverage target: 80%+ (happy-path, failure recording, disabled tracing,
lazy auto-init, store injection, filtered retrieval).

Test Categories:
    - TestInitTraceCapture: Initialisation with and without custom store
    - TestRunTracedSuccess: Successful execution records a SUCCESS trace
    - TestRunTracedFailure: Failed execution records a FAILED trace and re-raises
    - TestRunTracedDisabled: Disabled tracing is a transparent pass-through
    - TestRunTracedLazyInit: Auto-init when store is None but enabled=True
    - TestGetRecordedTraces: Retrieval, filtering, and empty-store behaviour
    - TestGetTraceStore: Store accessor returns expected value

.. versionadded:: 0.6.6
    Tests for MixinTraceCapture (OMN-2401)
"""

from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
from omnibase_core.mixins.mixin_trace_capture import MixinTraceCapture
from omnibase_core.models.trace.model_execution_trace import ModelExecutionTrace
from omnibase_core.models.trace_query.model_trace_query import ModelTraceQuery
from omnibase_core.services.trace.service_trace_in_memory_store import (
    ServiceTraceInMemoryStore,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _SimpleNode(MixinTraceCapture):
    """Minimal host class for testing the mixin standalone."""


async def _ok(value: str = "result") -> str:
    return value


async def _fail(message: str = "boom") -> str:
    raise RuntimeError(message)


# ---------------------------------------------------------------------------
# TestInitTraceCapture
# ---------------------------------------------------------------------------


class TestInitTraceCapture:
    def test_default_store_created(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()
        assert isinstance(node.get_trace_store(), ServiceTraceInMemoryStore)

    def test_custom_store_injected(self) -> None:
        node = _SimpleNode()
        custom = ServiceTraceInMemoryStore()
        node.init_trace_capture(store=custom)
        assert node.get_trace_store() is custom

    def test_disabled_leaves_store_none(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture(enabled=False)
        assert node.get_trace_store() is None
        assert node._trace_enabled is False

    def test_enabled_flag_set(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture(enabled=True)
        assert node._trace_enabled is True


# ---------------------------------------------------------------------------
# TestRunTracedSuccess
# ---------------------------------------------------------------------------


class TestRunTracedSuccess:
    async def test_returns_result_and_trace(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        result, trace = await node.run_traced(_ok("hello"))

        assert result == "hello"
        assert trace is not None
        assert isinstance(trace, ModelExecutionTrace)

    async def test_trace_status_is_success(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        _, trace = await node.run_traced(_ok())

        assert trace is not None
        assert trace.status == EnumExecutionStatus.SUCCESS
        assert trace.is_successful()

    async def test_trace_duration_is_positive(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        _, trace = await node.run_traced(_ok())

        assert trace is not None
        assert trace.get_duration_ms() >= 0.0

    async def test_trace_ids_auto_generated(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        _, trace = await node.run_traced(_ok())

        assert trace is not None
        assert isinstance(trace.trace_id, UUID)
        assert isinstance(trace.run_id, UUID)
        assert isinstance(trace.correlation_id, UUID)

    async def test_explicit_run_and_correlation_ids_used(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        run_id = uuid4()
        corr_id = uuid4()
        _, trace = await node.run_traced(
            _ok(),
            run_id=run_id,
            correlation_id=corr_id,
        )

        assert trace is not None
        assert trace.run_id == run_id
        assert trace.correlation_id == corr_id

    async def test_dispatch_id_propagated(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        dispatch_id = uuid4()
        _, trace = await node.run_traced(_ok(), dispatch_id=dispatch_id)

        assert trace is not None
        assert trace.dispatch_id == dispatch_id

    async def test_trace_persisted_to_store(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        _, trace = await node.run_traced(_ok())

        assert trace is not None
        stored = await node.get_trace_store().get(trace.trace_id)  # type: ignore[union-attr]
        assert stored == trace

    async def test_multiple_runs_accumulate(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        await node.run_traced(_ok("a"))
        await node.run_traced(_ok("b"))
        await node.run_traced(_ok("c"))

        traces = await node.get_recorded_traces()
        assert len(traces) == 3


# ---------------------------------------------------------------------------
# TestRunTracedFailure
# ---------------------------------------------------------------------------


class TestRunTracedFailure:
    async def test_exception_is_reraised(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        with pytest.raises(RuntimeError, match="boom"):
            await node.run_traced(_fail("boom"))

    async def test_failed_trace_is_persisted(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        with pytest.raises(RuntimeError):
            await node.run_traced(_fail())

        traces = await node.get_recorded_traces()
        assert len(traces) == 1
        assert traces[0].is_failure()

    async def test_failed_trace_status(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        with pytest.raises(RuntimeError):
            await node.run_traced(_fail())

        traces = await node.get_recorded_traces()
        assert traces[0].status == EnumExecutionStatus.FAILED

    async def test_failure_after_success_both_recorded(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        await node.run_traced(_ok())
        with pytest.raises(RuntimeError):
            await node.run_traced(_fail())

        all_traces = await node.get_recorded_traces()
        assert len(all_traces) == 2
        statuses = {t.status for t in all_traces}
        assert EnumExecutionStatus.SUCCESS in statuses
        assert EnumExecutionStatus.FAILED in statuses


# ---------------------------------------------------------------------------
# TestRunTracedDisabled
# ---------------------------------------------------------------------------


class TestRunTracedDisabled:
    async def test_disabled_returns_result_none_trace(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture(enabled=False)

        result, trace = await node.run_traced(_ok("data"))

        assert result == "data"
        assert trace is None

    async def test_disabled_no_store_operations(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture(enabled=False)

        await node.run_traced(_ok())

        # Store is None — nothing was written
        assert node.get_trace_store() is None

    async def test_disabled_exception_still_propagates(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture(enabled=False)

        with pytest.raises(RuntimeError, match="boom"):
            await node.run_traced(_fail("boom"))


# ---------------------------------------------------------------------------
# TestRunTracedLazyInit
# ---------------------------------------------------------------------------


class TestRunTracedLazyInit:
    async def test_lazy_auto_init_creates_store(self) -> None:
        # Do NOT call init_trace_capture — verify lazy path.
        node = _SimpleNode()
        node._trace_enabled = True
        # _trace_store is None (class default)

        result, trace = await node.run_traced(_ok("lazy"))

        assert result == "lazy"
        assert trace is not None
        assert node.get_trace_store() is not None

    async def test_lazy_auto_init_records_trace(self) -> None:
        node = _SimpleNode()
        node._trace_enabled = True

        _, trace = await node.run_traced(_ok())

        traces = await node.get_recorded_traces()
        assert len(traces) == 1
        assert traces[0] == trace


# ---------------------------------------------------------------------------
# TestGetRecordedTraces
# ---------------------------------------------------------------------------


class TestGetRecordedTraces:
    async def test_empty_before_any_run(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        traces = await node.get_recorded_traces()

        assert traces == []

    async def test_no_store_returns_empty(self) -> None:
        node = _SimpleNode()
        # No init_trace_capture call, no store

        traces = await node.get_recorded_traces()

        assert traces == []

    async def test_filter_by_success_status(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        await node.run_traced(_ok())
        with pytest.raises(RuntimeError):
            await node.run_traced(_fail())

        success_query = ModelTraceQuery(status=EnumExecutionStatus.SUCCESS)
        successes = await node.get_recorded_traces(filters=success_query)

        assert len(successes) == 1
        assert successes[0].is_successful()

    async def test_filter_by_failed_status(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        await node.run_traced(_ok())
        with pytest.raises(RuntimeError):
            await node.run_traced(_fail())

        fail_query = ModelTraceQuery(status=EnumExecutionStatus.FAILED)
        failures = await node.get_recorded_traces(filters=fail_query)

        assert len(failures) == 1
        assert failures[0].is_failure()

    async def test_filter_by_correlation_id(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        target_corr = uuid4()
        await node.run_traced(_ok(), correlation_id=target_corr)
        await node.run_traced(_ok())  # different correlation_id

        corr_query = ModelTraceQuery(correlation_id=target_corr)
        matched = await node.get_recorded_traces(filters=corr_query)

        assert len(matched) == 1
        assert matched[0].correlation_id == target_corr

    async def test_pagination_limit(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()

        for _ in range(5):
            await node.run_traced(_ok())

        limited = await node.get_recorded_traces(filters=ModelTraceQuery(limit=2))

        assert len(limited) == 2


# ---------------------------------------------------------------------------
# TestGetTraceStore
# ---------------------------------------------------------------------------


class TestGetTraceStore:
    def test_returns_none_before_init(self) -> None:
        node = _SimpleNode()
        assert node.get_trace_store() is None

    def test_returns_store_after_init(self) -> None:
        node = _SimpleNode()
        node.init_trace_capture()
        assert node.get_trace_store() is not None

    def test_returns_injected_store(self) -> None:
        node = _SimpleNode()
        custom = ServiceTraceInMemoryStore()
        node.init_trace_capture(store=custom)
        assert node.get_trace_store() is custom
