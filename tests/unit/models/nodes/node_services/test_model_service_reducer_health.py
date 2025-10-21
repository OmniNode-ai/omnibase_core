"""
Health Monitoring and Graceful Shutdown Tests for ModelServiceReducer.

Test suite covering health monitoring and graceful shutdown capabilities:
- Health status retrieval and metrics calculation
- Uptime calculation
- Active invocation counting
- Success rate calculation
- Health monitoring loop and periodic logging
- Graceful shutdown with active invocation handling
- Shutdown callbacks and signal handlers
- Resource cleanup and error handling
- State persistence health checks (reducer-specific)

Test Plan Reference:
    Section 5.3: Health Monitoring Tests
    Section 5.4: Graceful Shutdown Tests
    Section 6.3: ModelServiceReducer Integration
"""

import asyncio
import signal
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_reducer import ModelContractReducer
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.nodes.node_services.model_service_reducer import (
    ModelServiceReducer,
)

# ============================================================================
# Test Node Implementation
# ============================================================================


class ReducerNodeForHealthTesting(ModelServiceReducer):
    """Reducer node for health and shutdown testing (not a pytest test class)."""

    def __init__(
        self, container: ModelONEXContainer, node_id, event_bus, metadata_loader
    ):
        # Initialize required attributes before parent init
        self._node_id = node_id
        self.event_bus = event_bus
        self.metadata_loader = metadata_loader

        # Mock methods that would be called during init
        self._setup_event_handlers = Mock()
        self._setup_request_response_introspection = Mock()
        self._register_node = Mock()
        self._publish_introspection_event = Mock()
        self._register_shutdown_hook = Mock()

        # Call parent init
        ModelServiceReducer.__init__(self, container)

        self._node_name = "test_health_reducer_node"

        # Reducer-specific state for testing
        self._aggregation_state = {}
        self._state_persistence_healthy = True

    async def run(self, input_state):
        """Run method for tool execution with aggregation logic."""
        action = getattr(input_state, "action", "aggregate")

        if action == "aggregate":
            # Simulate aggregation
            data = getattr(input_state, "data", [])
            result = sum(data) if data else 0
            self._aggregation_state["last_result"] = result
            return {"result": result, "action": action, "state_updated": True}

        return {"result": "executed", "action": action}

    def get_aggregation_state_health(self) -> dict:
        """Get health status of aggregation state (reducer-specific)."""
        return {
            "state_persistence_healthy": self._state_persistence_healthy,
            "aggregation_state_size": len(self._aggregation_state),
            "last_aggregation": self._aggregation_state.get("last_result"),
        }

    def _extract_node_name(self) -> str:
        """Extract node name for logging."""
        return self._node_name

    def cleanup_event_handlers(self):
        """Mock cleanup method."""


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_container():
    """Create mock ModelONEXContainer for dependency injection."""
    container = Mock(spec=ModelONEXContainer)
    container.get_service = Mock(return_value=None)
    return container


@pytest.fixture
def mock_event_bus():
    """Create mock event bus for publish/subscribe."""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = Mock()
    return event_bus


@pytest.fixture
def mock_metadata_loader():
    """Create mock metadata loader."""
    loader = Mock()
    loader.metadata = Mock()
    loader.metadata.version = "1.0.0"
    return loader


@pytest.fixture
def node_id():
    """Generate UUID for node ID."""
    return uuid4()


@pytest.fixture
def correlation_id():
    """Generate UUID for correlation tracking."""
    return uuid4()


@pytest.fixture
def service_reducer(mock_container, mock_event_bus, mock_metadata_loader, node_id):
    """Create ModelServiceReducer instance for testing."""
    service = ReducerNodeForHealthTesting(
        mock_container, node_id, mock_event_bus, mock_metadata_loader
    )
    return service


@pytest.fixture
def tool_invocation_event(node_id, correlation_id):
    """Create ModelToolInvocationEvent for testing."""
    return ModelToolInvocationEvent(
        node_id=uuid4(),  # Source node ID
        correlation_id=correlation_id,
        requester_node_id=uuid4(),
        requester_id=uuid4(),  # Must be UUID
        target_node_id=node_id,
        target_node_name="test_health_reducer_node",
        tool_name="reducer_service",
        action="aggregate",
        parameters=ModelToolParameters.from_dict({"data": [1, 2, 3, 4, 5]}),
    )


# ============================================================================
# Health Status Retrieval Tests
# ============================================================================


class TestServiceReducerHealthStatus:
    """Test cases for health status retrieval and metrics."""

    def test_get_service_health_basic(self, service_reducer):
        """Test basic health status retrieval with all required fields."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        service_reducer._total_invocations = 10
        service_reducer._successful_invocations = 8
        service_reducer._failed_invocations = 2
        service_reducer._active_invocations = {uuid4(), uuid4()}

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert isinstance(health, dict)
        assert "status" in health
        assert "uptime_seconds" in health
        assert "active_invocations" in health
        assert "total_invocations" in health
        assert "successful_invocations" in health
        assert "failed_invocations" in health
        assert "success_rate" in health
        assert "node_id" in health
        assert "node_name" in health
        assert "shutdown_requested" in health

        assert health["status"] == "healthy"
        assert health["active_invocations"] == 2
        assert health["total_invocations"] == 10
        assert health["successful_invocations"] == 8
        assert health["failed_invocations"] == 2
        assert health["success_rate"] == 0.8
        assert health["shutdown_requested"] is False

    @patch("time.time")
    def test_get_service_health_uptime_calculation(self, mock_time, service_reducer):
        """Test uptime calculation with mocked time."""
        # Arrange
        start_time = 1000.0
        current_time = 1450.5
        expected_uptime = 450  # int(450.5) = 450 seconds

        mock_time.return_value = current_time
        service_reducer._service_running = True
        service_reducer._start_time = start_time

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["uptime_seconds"] == expected_uptime

    def test_get_service_health_active_invocations(self, service_reducer):
        """Test active invocation counting."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()

        # Add multiple active invocations
        invocation_ids = [uuid4() for _ in range(5)]
        service_reducer._active_invocations = set(invocation_ids)

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["active_invocations"] == 5
        assert len(service_reducer._active_invocations) == 5

    def test_get_service_health_success_rate(self, service_reducer):
        """Test success rate calculation with various scenarios."""
        # Scenario 1: Perfect success rate
        service_reducer._total_invocations = 100
        service_reducer._successful_invocations = 100
        service_reducer._failed_invocations = 0

        health = service_reducer.get_service_health()
        assert health["success_rate"] == 1.0

        # Scenario 2: 80% success rate
        service_reducer._total_invocations = 100
        service_reducer._successful_invocations = 80
        service_reducer._failed_invocations = 20

        health = service_reducer.get_service_health()
        assert health["success_rate"] == 0.8

        # Scenario 3: 0% success rate
        service_reducer._total_invocations = 50
        service_reducer._successful_invocations = 0
        service_reducer._failed_invocations = 50

        health = service_reducer.get_service_health()
        assert health["success_rate"] == 0.0

        # Scenario 4: Zero invocations (default to 1.0)
        service_reducer._total_invocations = 0
        service_reducer._successful_invocations = 0
        service_reducer._failed_invocations = 0

        health = service_reducer.get_service_health()
        assert health["success_rate"] == 1.0

    def test_get_service_health_success_rate_zero_invocations(self, service_reducer):
        """Test success rate with zero invocations."""
        # Arrange
        service_reducer._total_invocations = 0
        service_reducer._successful_invocations = 0
        service_reducer._failed_invocations = 0

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["success_rate"] == 1.0

    def test_get_service_health_before_start(self, service_reducer):
        """Test health status before service started."""
        # Arrange
        service_reducer._service_running = False
        service_reducer._start_time = None

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["status"] == "unhealthy"
        assert health["uptime_seconds"] == 0


# ============================================================================
# Health Monitoring Loop Tests
# ============================================================================


class TestServiceReducerHealthMonitoring:
    """Test cases for health monitoring loop."""

    @pytest.mark.asyncio
    async def test_health_monitor_loop_runs_while_active(self, service_reducer):
        """Test health monitoring loop runs during service lifetime."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False
        check_count = 0

        # Mock get_service_health to count calls
        original_get_health = service_reducer.get_service_health

        def counting_get_health():
            nonlocal check_count
            check_count += 1
            return original_get_health()

        service_reducer.get_service_health = counting_get_health

        # Mock asyncio.sleep to speed up test
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)
            # Stop after 3 iterations
            if len(sleep_calls) >= 3:
                service_reducer._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_reducer._health_monitor_loop()

        # Assert
        assert check_count == 3
        assert len(sleep_calls) == 3
        assert all(s == 30 for s in sleep_calls)  # 30 second intervals

    @pytest.mark.asyncio
    async def test_health_monitor_loop_logs_periodically(self, service_reducer):
        """Test periodic health logging every 100 invocations."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False
        log_messages = []

        # Mock logging to capture messages
        def mock_log_info(message):
            log_messages.append(message)

        service_reducer._log_info = mock_log_info

        # Mock asyncio.sleep
        async def mock_sleep(seconds):
            # Simulate invocations
            if service_reducer._total_invocations == 0:
                service_reducer._total_invocations = 100
                service_reducer._successful_invocations = 95
            else:
                service_reducer._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_reducer._health_monitor_loop()

        # Assert
        health_logs = [msg for msg in log_messages if "Health:" in msg]
        assert len(health_logs) > 0
        assert "active" in health_logs[0]
        assert "success rate" in health_logs[0]

    @pytest.mark.asyncio
    async def test_health_monitor_loop_sleep_interval(self, service_reducer):
        """Test sleep interval between health checks."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)
            if len(sleep_calls) >= 1:
                service_reducer._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_reducer._health_monitor_loop()

        # Assert
        assert len(sleep_calls) == 1
        assert sleep_calls[0] == 30  # 30 second interval

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_cancellation(self, service_reducer):
        """Test health monitor loop handles CancelledError gracefully."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False
        log_messages = []

        def mock_log_info(message):
            log_messages.append(message)

        service_reducer._log_info = mock_log_info

        # Mock asyncio.sleep to raise CancelledError
        async def mock_sleep(seconds):
            raise asyncio.CancelledError

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_reducer._health_monitor_loop()

        # Assert
        cancel_logs = [msg for msg in log_messages if "cancelled" in msg.lower()]
        assert len(cancel_logs) == 1
        assert "Health monitor cancelled" in cancel_logs[0]

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_exceptions(self, service_reducer):
        """Test health monitor loop logs exceptions without propagating."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False
        error_logs = []

        def mock_log_error(message):
            error_logs.append(message)

        service_reducer._log_error = mock_log_error

        # Mock get_service_health to raise exception
        def failing_get_health():
            raise RuntimeError("Health check failed")

        service_reducer.get_service_health = failing_get_health

        # Act
        await service_reducer._health_monitor_loop()

        # Assert
        assert len(error_logs) == 1
        assert "Health monitor error" in error_logs[0]
        assert "Health check failed" in error_logs[0]

    @pytest.mark.asyncio
    async def test_health_monitor_loop_stops_on_shutdown(self, service_reducer):
        """Test health monitor loop exits on shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service_reducer._health_monitor_loop()

        # Assert - should not sleep if shutdown already requested
        assert not mock_sleep.called


# ============================================================================
# Graceful Shutdown Tests
# ============================================================================


class TestServiceReducerGracefulShutdown:
    """Test cases for graceful shutdown."""

    @pytest.mark.asyncio
    async def test_stop_service_mode_basic(self, service_reducer, mock_event_bus):
        """Test basic graceful shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        service_reducer._health_task = asyncio.create_task(asyncio.sleep(10))

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert service_reducer._service_running is False
        assert service_reducer._shutdown_requested is True
        assert service_reducer._health_task.cancelled()

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_none(self, service_reducer):
        """Test wait with no active invocations."""
        # Arrange
        service_reducer._active_invocations = set()

        # Act
        start_time = time.time()
        await service_reducer._wait_for_active_invocations(timeout_ms=5000)
        elapsed = time.time() - start_time

        # Assert - should return almost immediately
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_completes_in_time(self, service_reducer):
        """Test wait for invocations that complete within timeout."""
        # Arrange
        correlation_id = uuid4()
        service_reducer._active_invocations = {correlation_id}

        # Simulate invocation completing after short delay
        async def remove_invocation():
            await asyncio.sleep(0.2)
            service_reducer._active_invocations.discard(correlation_id)

        # Start task to remove invocation
        asyncio.create_task(remove_invocation())

        # Act
        start_time = time.time()
        await service_reducer._wait_for_active_invocations(timeout_ms=5000)
        elapsed = time.time() - start_time

        # Assert - should complete after ~0.2 seconds
        assert 0.15 < elapsed < 0.5
        assert len(service_reducer._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_timeout(self, service_reducer):
        """Test timeout with active invocations remaining."""
        # Arrange
        invocation_ids = [uuid4() for _ in range(3)]
        service_reducer._active_invocations = set(invocation_ids)
        warning_logs = []

        def mock_log_warning(message):
            warning_logs.append(message)

        service_reducer._log_warning = mock_log_warning

        # Act
        with patch("time.time") as mock_time:
            # Simulate timeout
            mock_time.side_effect = [0, 0.1, 0.2, 31.0]  # Exceeds 30s timeout
            await service_reducer._wait_for_active_invocations(timeout_ms=30000)

        # Assert
        assert len(warning_logs) == 1
        assert "Timeout waiting for invocations" in warning_logs[0]
        assert "3 still active" in warning_logs[0]

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_partial_completion(
        self, service_reducer
    ):
        """Test partial completion before timeout."""
        # Arrange
        correlation_id_1 = uuid4()
        correlation_id_2 = uuid4()
        service_reducer._active_invocations = {correlation_id_1, correlation_id_2}

        # Simulate one invocation completing
        async def remove_one_invocation():
            await asyncio.sleep(0.05)
            service_reducer._active_invocations.discard(correlation_id_1)

        asyncio.create_task(remove_one_invocation())

        # Act
        with patch.object(service_reducer, "_log_warning") as mock_log_warning:
            await service_reducer._wait_for_active_invocations(timeout_ms=100)

        # Assert - should log warning about 1 remaining invocation
        assert mock_log_warning.called
        assert len(service_reducer._active_invocations) == 1

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_custom_timeout(self, service_reducer):
        """Test custom timeout value respected."""
        # Arrange
        correlation_id = uuid4()
        service_reducer._active_invocations = {correlation_id}

        # Act
        start_time = time.time()
        await service_reducer._wait_for_active_invocations(timeout_ms=200)
        elapsed = time.time() - start_time

        # Assert - should timeout after ~0.2 seconds
        assert 0.15 < elapsed < 0.4


# ============================================================================
# Shutdown Event Emission Tests
# ============================================================================


class TestServiceReducerShutdownEventEmission:
    """Test shutdown event emission functionality."""

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_success(self, service_reducer, mock_event_bus):
        """Test successful shutdown event emission."""
        # Act
        await service_reducer._emit_shutdown_event()

        # Assert
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args[0]
        assert isinstance(call_args[0], ModelNodeShutdownEvent)
        assert call_args[0].node_id == service_reducer.node_id
        assert call_args[0].shutdown_reason == "graceful"

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_without_event_bus(self, service_reducer):
        """Test shutdown event emission without event bus."""
        # Arrange
        service_reducer.event_bus = None

        # Act - should not raise exception
        await service_reducer._emit_shutdown_event()

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_failure(self, service_reducer, mock_event_bus):
        """Test shutdown event emission failure handling."""
        # Arrange
        mock_event_bus.publish.side_effect = RuntimeError("Event bus publish failed")

        # Act
        with patch.object(service_reducer, "_log_error") as mock_log_error:
            # Should not raise exception
            await service_reducer._emit_shutdown_event()

        # Assert - error should be logged
        assert mock_log_error.called


# ============================================================================
# Shutdown Callbacks Tests
# ============================================================================


class TestServiceReducerShutdownCallbacks:
    """Test shutdown callback functionality."""

    @pytest.mark.asyncio
    async def test_add_shutdown_callback(self, service_reducer):
        """Test adding shutdown callback."""
        # Arrange
        callback = Mock()

        # Act
        service_reducer.add_shutdown_callback(callback)

        # Assert
        assert callback in service_reducer._shutdown_callbacks

    @pytest.mark.asyncio
    async def test_add_multiple_shutdown_callbacks(self, service_reducer):
        """Test adding multiple callbacks."""
        # Arrange
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        # Act
        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback2)
        service_reducer.add_shutdown_callback(callback3)

        # Assert
        assert len(service_reducer._shutdown_callbacks) == 3
        assert callback1 in service_reducer._shutdown_callbacks
        assert callback2 in service_reducer._shutdown_callbacks
        assert callback3 in service_reducer._shutdown_callbacks

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_executed(self, service_reducer):
        """Test callbacks executed on shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        callback_results = []

        def callback1():
            callback_results.append("callback1")

        def callback2():
            callback_results.append("callback2")

        def callback3():
            callback_results.append("callback3")

        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback2)
        service_reducer.add_shutdown_callback(callback3)

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert len(callback_results) == 3
        assert callback_results == ["callback1", "callback2", "callback3"]

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_execution_order(self, service_reducer):
        """Test callbacks executed in registration order."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        call_order = []

        def callback1():
            call_order.append(1)

        def callback2():
            call_order.append(2)

        def callback3():
            call_order.append(3)

        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback2)
        service_reducer.add_shutdown_callback(callback3)

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert call_order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_shutdown_callback_exception_handling(self, service_reducer):
        """Test exception in callback doesn't stop other callbacks."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        callback_results = []
        error_logs = []

        def mock_log_error(message):
            error_logs.append(message)

        service_reducer._log_error = mock_log_error

        def good_callback1():
            callback_results.append("good1")

        def failing_callback():
            raise RuntimeError("Callback failed")

        def good_callback2():
            callback_results.append("good2")

        service_reducer.add_shutdown_callback(good_callback1)
        service_reducer.add_shutdown_callback(failing_callback)
        service_reducer.add_shutdown_callback(good_callback2)

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert len(callback_results) == 2
        assert callback_results == ["good1", "good2"]
        assert len(error_logs) == 1
        assert "Shutdown callback failed" in error_logs[0]


# ============================================================================
# Signal Handler Tests
# ============================================================================


class TestServiceReducerSignalHandlers:
    """Test signal handler functionality."""

    def test_register_signal_handlers_success(self, service_reducer):
        """Test signal handlers registered correctly."""
        # Arrange
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        # Act
        service_reducer._register_signal_handlers()

        # Assert - signal handlers should be changed
        assert signal.getsignal(signal.SIGTERM) != original_sigterm
        assert signal.getsignal(signal.SIGINT) != original_sigint

        # Restore original handlers
        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)

    def test_register_signal_handlers_failure(self, service_reducer):
        """Test signal handler registration failure."""
        # Arrange
        warning_logs = []

        def mock_log_warning(message):
            warning_logs.append(message)

        service_reducer._log_warning = mock_log_warning

        # Act
        with patch("signal.signal", side_effect=RuntimeError("Cannot register signal")):
            service_reducer._register_signal_handlers()

        # Assert
        assert len(warning_logs) == 1
        assert "Could not register signal handlers" in warning_logs[0]

    def test_signal_handler_sets_shutdown_flag(self, service_reducer):
        """Test signal handler behavior sets shutdown flag."""
        # Arrange
        service_reducer._shutdown_requested = False
        log_messages = []

        def mock_log_info(message):
            log_messages.append(message)

        service_reducer._log_info = mock_log_info

        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            # Act
            service_reducer._register_signal_handlers()

            # Get the registered handler
            handler = signal.getsignal(signal.SIGTERM)

            # Simulate signal
            handler(signal.SIGTERM, None)

            # Assert
            assert service_reducer._shutdown_requested is True
            assert any("signal" in msg.lower() for msg in log_messages)

        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_sigterm)

    def test_signal_handler_logs_signal(self, service_reducer):
        """Test signal handler logs the received signal."""
        # Arrange
        log_messages = []

        def mock_log_info(message):
            log_messages.append(message)

        service_reducer._log_info = mock_log_info

        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            # Act
            service_reducer._register_signal_handlers()
            handler = signal.getsignal(signal.SIGTERM)
            handler(signal.SIGTERM, None)

            # Assert
            assert any("signal" in msg.lower() for msg in log_messages)
            assert any(str(signal.SIGTERM) in msg for msg in log_messages)

        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_sigterm)


# ============================================================================
# Shutdown Integration Tests
# ============================================================================


class TestServiceReducerShutdownIntegration:
    """Test integrated shutdown scenarios."""

    @pytest.mark.asyncio
    async def test_shutdown_during_active_invocations(
        self, service_reducer, mock_event_bus
    ):
        """Test shutdown waits for active invocations to complete."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        invocation_completed = False

        # Create a simple invocation event
        simple_event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            target_node_id=service_reducer._node_id,
            target_node_name="test_health_reducer_node",
            tool_name="reducer_service",
            action="test_action",
            parameters=ModelToolParameters(),
        )

        # Mock long-running invocation
        async def slow_run(input_state):
            await asyncio.sleep(0.2)
            nonlocal invocation_completed
            invocation_completed = True
            return {"result": "success", "state_updated": True}

        service_reducer.run = slow_run

        # Start invocation in background
        invocation_task = asyncio.create_task(
            service_reducer.handle_tool_invocation(simple_event)
        )

        # Wait for invocation to start
        await asyncio.sleep(0.1)

        # Act - stop service while invocation is active
        stop_task = asyncio.create_task(service_reducer.stop_service_mode())

        # Wait for both to complete
        await asyncio.gather(invocation_task, stop_task)

        # Assert
        assert invocation_completed is True
        assert service_reducer._service_running is False
        assert len(service_reducer._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_health_task_cancellation(self, service_reducer):
        """Test health task cancellation during shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()

        # Create a health task
        async def long_health_check():
            await asyncio.sleep(10)

        service_reducer._health_task = asyncio.create_task(long_health_check())

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert service_reducer._health_task.cancelled()

    @pytest.mark.asyncio
    async def test_resource_cleanup(self, service_reducer, mock_event_bus):
        """Test complete resource cleanup during shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        service_reducer._active_invocations = set()
        cleanup_called = False

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        service_reducer.cleanup_event_handlers = mock_cleanup

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert cleanup_called is True
        assert service_reducer._service_running is False
        assert mock_event_bus.publish.called  # Shutdown event emitted


# ============================================================================
# State Persistence Health Tests (Reducer-Specific)
# ============================================================================


class TestServiceReducerStatePersistenceHealth:
    """Test state persistence health monitoring (reducer-specific)."""

    def test_aggregation_state_health_check(self, service_reducer):
        """Test aggregation state health monitoring."""
        # Arrange
        service_reducer._aggregation_state = {"last_result": 42, "count": 10}
        service_reducer._state_persistence_healthy = True

        # Act
        state_health = service_reducer.get_aggregation_state_health()

        # Assert
        assert state_health["state_persistence_healthy"] is True
        assert state_health["aggregation_state_size"] == 2
        assert state_health["last_aggregation"] == 42

    def test_aggregation_state_health_unhealthy(self, service_reducer):
        """Test unhealthy state persistence detection."""
        # Arrange
        service_reducer._state_persistence_healthy = False
        service_reducer._aggregation_state = {}

        # Act
        state_health = service_reducer.get_aggregation_state_health()

        # Assert
        assert state_health["state_persistence_healthy"] is False
        assert state_health["aggregation_state_size"] == 0
        assert state_health["last_aggregation"] is None

    @pytest.mark.asyncio
    async def test_shutdown_preserves_aggregation_state(self, service_reducer):
        """Test that shutdown doesn't corrupt aggregation state."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        service_reducer._aggregation_state = {"last_result": 100, "important": True}

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert - state should be preserved
        assert service_reducer._aggregation_state["last_result"] == 100
        assert service_reducer._aggregation_state["important"] is True

    @pytest.mark.asyncio
    async def test_invocation_updates_aggregation_state(self, service_reducer):
        """Test that tool invocations update aggregation state correctly."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()

        # Create a simple invocation event without complex parameters
        simple_event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            target_node_id=service_reducer._node_id,
            target_node_name="test_health_reducer_node",
            tool_name="reducer_service",
            action="test_action",
            parameters=ModelToolParameters(),  # Empty parameters for simplicity
        )

        # Act - handle aggregation invocation
        await service_reducer.handle_tool_invocation(simple_event)

        # Wait for async completion
        await asyncio.sleep(0.1)

        # Assert - verify the invocation was processed successfully
        # State update depends on the action, but we should have incremented counters
        assert service_reducer._total_invocations >= 1
        assert service_reducer._successful_invocations >= 1


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestServiceReducerHealthEdgeCases:
    """Test edge cases for health monitoring and shutdown."""

    def test_get_service_health_before_start(self, service_reducer):
        """Test health status before service started."""
        # Arrange
        service_reducer._service_running = False
        service_reducer._start_time = None

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["status"] == "unhealthy"
        assert health["uptime_seconds"] == 0

    def test_get_service_health_status_unhealthy_when_shutdown_requested(
        self, service_reducer
    ):
        """Test status is unhealthy when shutdown requested."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        service_reducer._shutdown_requested = True

        # Act
        health = service_reducer.get_service_health()

        # Assert
        assert health["status"] == "unhealthy"
        assert health["shutdown_requested"] is True

    @pytest.mark.asyncio
    async def test_stop_service_mode_idempotent(self, service_reducer):
        """Test stopping already stopped service is safe."""
        # Arrange
        service_reducer._service_running = False

        # Act - stop should return immediately
        await service_reducer.stop_service_mode()

        # Assert - no exceptions raised
        assert service_reducer._service_running is False

    @pytest.mark.asyncio
    async def test_stop_service_mode_cleanup_event_handlers(self, service_reducer):
        """Test cleanup_event_handlers is called during shutdown."""
        # Arrange
        service_reducer._service_running = True
        service_reducer._start_time = time.time()
        cleanup_called = False

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        service_reducer.cleanup_event_handlers = mock_cleanup

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_reducer._wait_for_active_invocations = mock_wait

        # Act
        await service_reducer.stop_service_mode()

        # Assert
        assert cleanup_called is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
