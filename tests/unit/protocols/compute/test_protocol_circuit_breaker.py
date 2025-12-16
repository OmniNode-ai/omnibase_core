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

from omnibase_core.models.configuration.model_circuit_breaker import (
    ModelCircuitBreaker,
)
from omnibase_core.protocols.compute import (
    ProtocolAsyncCircuitBreaker,
    ProtocolCircuitBreaker,
)

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
    Adapter to make ModelCircuitBreaker conform to ProtocolCircuitBreaker.

    ModelCircuitBreaker uses different method names:
    - reset_state() instead of reset()

    This adapter demonstrates how existing implementations can conform.
    """

    def __init__(self, breaker: ModelCircuitBreaker | None = None):
        self._breaker = breaker or ModelCircuitBreaker()

    @property
    def is_open(self) -> bool:
        return self._breaker.state == "open"

    @property
    def failure_count(self) -> int:
        return self._breaker.failure_count

    def record_success(self) -> None:
        self._breaker.record_success()

    def record_failure(self, correlation_id: UUID | None = None) -> None:
        self._breaker.record_failure()

    def reset(self) -> None:
        self._breaker.reset_state()


# =============================================================================
# Test Classes
# =============================================================================


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


class TestModelCircuitBreakerAdapterConformance:
    """Test that ModelCircuitBreaker can conform via adapter."""

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
            execute_with_breaker(cb, lambda: (_ for _ in ()).throw(ValueError("fail")))

        with pytest.raises(ValueError):
            execute_with_breaker(cb, lambda: (_ for _ in ()).throw(ValueError("fail")))

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
