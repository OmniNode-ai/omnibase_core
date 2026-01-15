"""
Tests for ProtocolCircuitBreaker and ProtocolAsyncCircuitBreaker.

Validates:
1. Protocol definitions are correctly structured
2. runtime_checkable decorator works for isinstance checks
3. Mock implementations conform to protocols
4. ModelCircuitBreaker conforms to ProtocolCircuitBreaker
5. Async implementations conform to ProtocolAsyncCircuitBreaker

Related:
    - OMN-861: Define ProtocolCircuitBreaker interface
"""

import asyncio
from collections.abc import Callable
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_circuit_breaker_state import EnumCircuitBreakerState
from omnibase_core.models.configuration.model_circuit_breaker import (
    ModelCircuitBreaker,
)
from omnibase_core.protocols.compute import (
    ProtocolAsyncCircuitBreaker,
    ProtocolCircuitBreaker,
)

# =============================================================================
# Test Helpers
# =============================================================================


def _raise_value_error() -> None:
    """Helper function to raise ValueError for testing."""
    raise ValueError("fail")


# =============================================================================
# Test Fixtures - Mock Implementations
# =============================================================================


class MockSyncCircuitBreaker:
    """Minimal sync circuit breaker for protocol conformance testing."""

    def __init__(self, failure_threshold: int = 5):
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._is_open = False

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def record_success(self) -> None:
        self._failure_count = 0
        self._is_open = False

    def record_failure(self, correlation_id: UUID | None = None) -> None:
        self._failure_count += 1
        if self._failure_count >= self._failure_threshold:
            self._is_open = True

    def reset(self) -> None:
        self._failure_count = 0
        self._is_open = False


class MockAsyncCircuitBreaker:
    """Minimal async circuit breaker for protocol conformance testing."""

    def __init__(self, failure_threshold: int = 5):
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._is_open = False
        self._lock = asyncio.Lock()

    @property
    def is_open(self) -> bool:
        return self._is_open

    @property
    def failure_count(self) -> int:
        return self._failure_count

    async def record_success(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._is_open = False

    async def record_failure(self, correlation_id: UUID | None = None) -> None:
        async with self._lock:
            self._failure_count += 1
            if self._failure_count >= self._failure_threshold:
                self._is_open = True

    async def reset(self) -> None:
        async with self._lock:
            self._failure_count = 0
            self._is_open = False


class ModelCircuitBreakerAdapter:
    """
    Adapter to demonstrate protocol conformance patterns.

    While ModelCircuitBreaker now directly conforms to ProtocolCircuitBreaker,
    this adapter shows how to wrap existing implementations that may have
    different method names or interfaces.
    """

    def __init__(self, breaker: ModelCircuitBreaker | None = None):
        self._breaker = breaker or ModelCircuitBreaker()

    @property
    def is_open(self) -> bool:
        return self._breaker.state == EnumCircuitBreakerState.OPEN

    @property
    def failure_count(self) -> int:
        return self._breaker.failure_count

    def record_success(self) -> None:
        self._breaker.record_success()

    def record_failure(self, correlation_id: UUID | None = None) -> None:
        self._breaker.record_failure(correlation_id)

    def reset(self) -> None:
        self._breaker.reset_state()


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestProtocolCircuitBreakerDefinition:
    """Test ProtocolCircuitBreaker protocol definition."""

    def test_protocol_is_runtime_checkable(self):
        """Verify protocol has @runtime_checkable decorator."""
        mock = MockSyncCircuitBreaker()
        assert isinstance(mock, ProtocolCircuitBreaker)

    def test_non_conforming_class_fails_isinstance(self):
        """Verify isinstance returns False for non-conforming classes."""

        class NotACircuitBreaker:
            pass

        obj = NotACircuitBreaker()
        assert not isinstance(obj, ProtocolCircuitBreaker)

    def test_partial_implementation_fails_isinstance(self):
        """Verify partial implementations don't pass isinstance."""

        class PartialCircuitBreaker:
            @property
            def is_open(self) -> bool:
                return False

            # Missing: failure_count, record_success, record_failure, reset

        obj = PartialCircuitBreaker()
        assert not isinstance(obj, ProtocolCircuitBreaker)

    def test_protocol_methods_exist(self):
        """Verify protocol defines expected methods."""
        mock = MockSyncCircuitBreaker()

        # Properties
        assert hasattr(mock, "is_open")
        assert hasattr(mock, "failure_count")

        # Methods
        assert callable(getattr(mock, "record_success", None))
        assert callable(getattr(mock, "record_failure", None))
        assert callable(getattr(mock, "reset", None))


@pytest.mark.unit
class TestProtocolAsyncCircuitBreakerDefinition:
    """Test ProtocolAsyncCircuitBreaker protocol definition."""

    def test_async_protocol_is_runtime_checkable(self):
        """Verify async protocol has @runtime_checkable decorator."""
        mock = MockAsyncCircuitBreaker()
        assert isinstance(mock, ProtocolAsyncCircuitBreaker)

    def test_non_conforming_class_fails_isinstance(self):
        """Verify isinstance returns False for non-conforming classes."""

        class NotAnAsyncCircuitBreaker:
            pass

        obj = NotAnAsyncCircuitBreaker()
        assert not isinstance(obj, ProtocolAsyncCircuitBreaker)

    def test_sync_impl_passes_runtime_check_but_not_type_check(self):
        """
        Verify sync implementation passes runtime isinstance check.

        Note: Python's @runtime_checkable only checks for method/property names,
        NOT for async vs sync signatures. Static type checkers (mypy, pyright)
        will catch the distinction, but isinstance() cannot.

        This is a known limitation of runtime_checkable protocols.
        See: https://docs.python.org/3/library/typing.html#typing.runtime_checkable
        """
        sync_mock = MockSyncCircuitBreaker()
        # Runtime check passes (only checks names exist)
        # Static type checkers would flag this as incompatible
        assert isinstance(sync_mock, ProtocolAsyncCircuitBreaker)

        # But we can verify the methods aren't actually async
        assert not asyncio.iscoroutinefunction(sync_mock.record_success)
        assert not asyncio.iscoroutinefunction(sync_mock.record_failure)
        assert not asyncio.iscoroutinefunction(sync_mock.reset)


@pytest.mark.unit
class TestMockSyncCircuitBreakerBehavior:
    """Test MockSyncCircuitBreaker behavior for protocol conformance."""

    def test_initial_state(self):
        """Verify initial state is closed."""
        cb = MockSyncCircuitBreaker()
        assert not cb.is_open
        assert cb.failure_count == 0

    def test_record_failure_increments_count(self):
        """Verify record_failure increments failure count."""
        cb = MockSyncCircuitBreaker(failure_threshold=5)
        cb.record_failure()
        assert cb.failure_count == 1
        assert not cb.is_open

    def test_failure_threshold_opens_circuit(self):
        """Verify circuit opens after reaching failure threshold."""
        cb = MockSyncCircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open

        cb.record_failure()  # 3rd failure
        assert cb.is_open

    def test_record_success_resets_state(self):
        """Verify record_success resets failure count and closes circuit."""
        cb = MockSyncCircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()  # Opens circuit
        assert cb.is_open

        cb.record_success()
        assert not cb.is_open
        assert cb.failure_count == 0

    def test_reset_clears_state(self):
        """Verify reset clears all state."""
        cb = MockSyncCircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open

        cb.reset()
        assert not cb.is_open
        assert cb.failure_count == 0

    def test_correlation_id_accepted(self):
        """Verify record_failure accepts optional correlation_id."""
        cb = MockSyncCircuitBreaker()
        correlation_id = uuid4()

        # Should not raise
        cb.record_failure(correlation_id=correlation_id)
        assert cb.failure_count == 1

        # Also test with None explicitly
        cb.record_failure(correlation_id=None)
        assert cb.failure_count == 2


@pytest.mark.unit
class TestMockAsyncCircuitBreakerBehavior:
    """Test MockAsyncCircuitBreaker behavior for protocol conformance."""

    @pytest.mark.asyncio
    async def test_initial_state(self):
        """Verify initial state is closed."""
        cb = MockAsyncCircuitBreaker()
        assert not cb.is_open
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_record_failure_increments_count(self):
        """Verify record_failure increments failure count."""
        cb = MockAsyncCircuitBreaker(failure_threshold=5)
        await cb.record_failure()
        assert cb.failure_count == 1
        assert not cb.is_open

    @pytest.mark.asyncio
    async def test_failure_threshold_opens_circuit(self):
        """Verify circuit opens after reaching failure threshold."""
        cb = MockAsyncCircuitBreaker(failure_threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        assert not cb.is_open

        await cb.record_failure()  # 3rd failure
        assert cb.is_open

    @pytest.mark.asyncio
    async def test_record_success_resets_state(self):
        """Verify record_success resets failure count and closes circuit."""
        cb = MockAsyncCircuitBreaker(failure_threshold=2)
        await cb.record_failure()
        await cb.record_failure()  # Opens circuit
        assert cb.is_open

        await cb.record_success()
        assert not cb.is_open
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """Verify reset clears all state."""
        cb = MockAsyncCircuitBreaker(failure_threshold=2)
        await cb.record_failure()
        await cb.record_failure()
        assert cb.is_open

        await cb.reset()
        assert not cb.is_open
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_correlation_id_accepted(self):
        """Verify record_failure accepts optional correlation_id."""
        cb = MockAsyncCircuitBreaker()
        correlation_id = uuid4()

        # Should not raise
        await cb.record_failure(correlation_id=correlation_id)
        assert cb.failure_count == 1


@pytest.mark.unit
class TestModelCircuitBreakerDirectConformance:
    """Test that ModelCircuitBreaker directly conforms to ProtocolCircuitBreaker."""

    def test_model_directly_conforms_to_protocol(self):
        """Verify ModelCircuitBreaker directly satisfies ProtocolCircuitBreaker."""
        breaker = ModelCircuitBreaker()
        assert isinstance(breaker, ProtocolCircuitBreaker)

    def test_model_initial_state(self):
        """Verify model reports correct initial state via protocol interface."""
        breaker = ModelCircuitBreaker()
        assert not breaker.is_open
        assert breaker.failure_count == 0

    def test_model_is_open_property(self):
        """Verify is_open property correctly reflects state."""
        breaker = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)

        # Initially closed
        assert not breaker.is_open
        assert breaker.state == EnumCircuitBreakerState.CLOSED

        # After enough failures, should be open
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open
        assert breaker.state == EnumCircuitBreakerState.OPEN

    def test_model_record_failure_with_correlation_id(self):
        """Verify record_failure accepts optional correlation_id."""
        breaker = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)
        correlation_id = uuid4()

        # Should not raise
        breaker.record_failure(correlation_id=correlation_id)
        assert breaker.failure_count == 1

        # Also test with None explicitly
        breaker.record_failure(correlation_id=None)
        assert breaker.failure_count == 2

    def test_model_reset_method(self):
        """Verify reset() method works and is equivalent to reset_state()."""
        breaker = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)

        # Trigger failures to open circuit
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.is_open
        assert breaker.failure_count == 2

        # Reset via protocol method
        breaker.reset()
        assert not breaker.is_open
        assert breaker.failure_count == 0
        assert breaker.state == EnumCircuitBreakerState.CLOSED

    def test_model_reset_and_reset_state_equivalent(self):
        """Verify reset() and reset_state() are functionally equivalent."""
        breaker1 = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)
        breaker2 = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)

        # Put both in same state
        breaker1.record_failure()
        breaker1.record_failure()
        breaker2.record_failure()
        breaker2.record_failure()

        # Reset using different methods
        breaker1.reset()
        breaker2.reset_state()

        # Both should have same end state
        assert breaker1.state == breaker2.state == EnumCircuitBreakerState.CLOSED
        assert breaker1.failure_count == breaker2.failure_count == 0
        assert breaker1.success_count == breaker2.success_count == 0
        assert breaker1.total_requests == breaker2.total_requests == 0

    def test_correlation_id_tracking_pattern(self):
        """Demonstrate correlation_id usage for distributed tracing.

        The correlation_id parameter enables tracking failures across
        distributed systems by associating each failure with a trace ID.
        This is useful for:
        - Correlating circuit breaker state with distributed traces
        - Aggregating failure metrics by request/trace
        - Debugging which requests triggered state changes
        """
        breaker = ModelCircuitBreaker()
        trace_id = uuid4()

        # Record failure with correlation ID for tracing
        breaker.record_failure(correlation_id=trace_id)

        # Verify failure was recorded
        assert breaker.failure_count == 1

        # Multiple failures can share the same trace ID (e.g., retries)
        breaker.record_failure(correlation_id=trace_id)
        assert breaker.failure_count == 2

        # Different trace IDs for independent requests
        other_trace_id = uuid4()
        breaker.record_failure(correlation_id=other_trace_id)
        assert breaker.failure_count == 3

    def test_model_protocol_usage_pattern(self):
        """Test that ModelCircuitBreaker works in protocol-typed function."""

        def execute_with_breaker(
            cb: ProtocolCircuitBreaker,
            operation: Callable[[], object],
        ) -> object:
            """Execute operation with circuit breaker protection."""
            if cb.is_open:
                raise RuntimeError("Circuit is open")

            try:
                result = operation()
                cb.record_success()
                return result
            except Exception:
                cb.record_failure()
                raise

        # Use ModelCircuitBreaker directly (no adapter needed)
        # Note: ModelCircuitBreaker uses failure_rate_threshold (default 0.5) in
        # addition to absolute failure_threshold. We set failure_rate_threshold=1.0
        # to rely only on absolute failure count for predictable test behavior.
        breaker: ProtocolCircuitBreaker = ModelCircuitBreaker(
            failure_threshold=2,
            minimum_request_threshold=1,
            failure_rate_threshold=1.0,  # Disable rate-based tripping
        )

        # Successful operation
        result = execute_with_breaker(breaker, lambda: "success")
        assert result == "success"

        # First failure - circuit still closed
        with pytest.raises(ValueError):
            execute_with_breaker(breaker, _raise_value_error)
        assert not breaker.is_open

        # Second failure - circuit should now open
        with pytest.raises(ValueError):
            execute_with_breaker(breaker, _raise_value_error)

        # Circuit should now be open
        assert breaker.is_open

        with pytest.raises(RuntimeError, match="Circuit is open"):
            execute_with_breaker(breaker, lambda: "should not run")

        # Reset and retry
        breaker.reset()
        assert not breaker.is_open
        result = execute_with_breaker(breaker, lambda: "recovered")
        assert result == "recovered"


@pytest.mark.unit
class TestModelCircuitBreakerAdapterConformance:
    """Test that ModelCircuitBreaker can still conform via adapter (backwards compat)."""

    def test_adapter_conforms_to_protocol(self):
        """Verify adapter satisfies ProtocolCircuitBreaker."""
        adapter = ModelCircuitBreakerAdapter()
        assert isinstance(adapter, ProtocolCircuitBreaker)

    def test_adapter_initial_state(self):
        """Verify adapter reports correct initial state."""
        adapter = ModelCircuitBreakerAdapter()
        assert not adapter.is_open
        assert adapter.failure_count == 0

    def test_adapter_record_failure(self):
        """Verify adapter correctly delegates record_failure."""
        breaker = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)
        adapter = ModelCircuitBreakerAdapter(breaker)

        adapter.record_failure()
        assert adapter.failure_count == 1

    def test_adapter_record_success(self):
        """Verify adapter correctly delegates record_success."""
        adapter = ModelCircuitBreakerAdapter()
        adapter.record_success()
        # Should not raise, success is recorded

    def test_adapter_reset(self):
        """Verify adapter correctly delegates reset."""
        breaker = ModelCircuitBreaker(failure_threshold=2, minimum_request_threshold=1)
        adapter = ModelCircuitBreakerAdapter(breaker)

        adapter.record_failure()
        adapter.record_failure()
        adapter.reset()

        assert adapter.failure_count == 0


@pytest.mark.unit
class TestProtocolUsagePatterns:
    """Test common usage patterns with protocols."""

    def test_function_accepting_protocol(self):
        """Test function that accepts ProtocolCircuitBreaker."""

        def execute_with_breaker(
            cb: ProtocolCircuitBreaker,
            operation: Callable[[], object],
        ) -> object:
            """Execute operation with circuit breaker protection."""
            if cb.is_open:
                raise RuntimeError("Circuit is open")

            try:
                result = operation()
                cb.record_success()
                return result
            except Exception:
                cb.record_failure()
                raise

        cb = MockSyncCircuitBreaker(failure_threshold=2)

        # Successful operation
        result = execute_with_breaker(cb, lambda: "success")
        assert result == "success"

        # Failed operations
        with pytest.raises(ValueError):
            execute_with_breaker(cb, _raise_value_error)

        with pytest.raises(ValueError):
            execute_with_breaker(cb, _raise_value_error)

        # Circuit should now be open
        assert cb.is_open

        with pytest.raises(RuntimeError, match="Circuit is open"):
            execute_with_breaker(cb, lambda: "should not run")

    def test_type_annotation_works(self):
        """Test that type annotations work with protocol."""

        def get_failure_count(cb: ProtocolCircuitBreaker) -> int:
            return cb.failure_count

        mock: ProtocolCircuitBreaker = MockSyncCircuitBreaker()
        assert get_failure_count(mock) == 0

        mock.record_failure()
        assert get_failure_count(mock) == 1


@pytest.mark.unit
class TestProtocolImports:
    """Test that protocols are correctly exported."""

    def test_import_from_compute_module(self):
        """Test imports from omnibase_core.protocols.compute."""
        from omnibase_core.protocols.compute import (
            ProtocolAsyncCircuitBreaker,
            ProtocolCircuitBreaker,
        )

        assert ProtocolCircuitBreaker is not None
        assert ProtocolAsyncCircuitBreaker is not None

    def test_import_from_protocol_file(self):
        """Test direct imports from protocol file."""
        from omnibase_core.protocols.compute.protocol_circuit_breaker import (
            ProtocolAsyncCircuitBreaker,
            ProtocolCircuitBreaker,
        )

        assert ProtocolCircuitBreaker is not None
        assert ProtocolAsyncCircuitBreaker is not None
