"""
Unit tests for ModelServiceCompute health monitoring and graceful shutdown.

Tests all aspects of service health monitoring and shutdown:
- Health status retrieval and metrics
- Uptime calculation
- Active invocation counting
- Success rate calculation
- Health monitoring loop
- Periodic health logging
- Graceful shutdown
- Active invocation wait timeout
- Shutdown event emission
- Shutdown callback execution
- Signal handlers
- Shutdown during active invocation
- Health task cancellation
- Resource cleanup

All tests use mocking to ensure deterministic behavior and fast execution.
"""

import asyncio
import signal
import time
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.service.model_service_compute import ModelServiceCompute


class ComputeNodeForHealthTesting(ModelServiceCompute):
    """Compute node for health and shutdown testing (not a pytest test class)."""

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
        ModelServiceCompute.__init__(self, container)

        self._node_name = "test_health_compute_node"

    async def run(self, input_state):
        """Run method for tool execution."""
        return {"result": "executed", "action": getattr(input_state, "action", "test")}

    def _extract_node_name(self) -> str:
        """Extract node name for logging."""
        return self._node_name

    def cleanup_event_handlers(self):
        """Mock cleanup method."""


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
def service_compute(mock_container, mock_event_bus, mock_metadata_loader, node_id):
    """Create ModelServiceCompute instance for testing."""
    service = ComputeNodeForHealthTesting(
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
        target_node_name="test_health_compute_node",
        tool_name="compute_service",
        action="transform",
        parameters={"data": "input"},
    )


class TestModelServiceComputeHealthStatus:
    """Test cases for health status retrieval and metrics."""

    def test_get_service_health_basic(self, service_compute):
        """Test basic health status retrieval with all required fields."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        service_compute._total_invocations = 10
        service_compute._successful_invocations = 8
        service_compute._failed_invocations = 2
        service_compute._active_invocations = {uuid4(), uuid4()}

        # Act
        health = service_compute.get_service_health()

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
    def test_get_service_health_uptime_calculation(self, mock_time, service_compute):
        """Test uptime calculation with mocked time."""
        # Arrange
        start_time = 1000.0
        current_time = 1450.5
        expected_uptime = 450  # int(450.5) = 450 seconds

        mock_time.return_value = current_time
        service_compute._service_running = True
        service_compute._start_time = start_time

        # Act
        health = service_compute.get_service_health()

        # Assert
        assert health["uptime_seconds"] == expected_uptime

    def test_get_service_health_active_invocations(self, service_compute):
        """Test active invocation counting."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()

        # Add multiple active invocations
        invocation_ids = [uuid4() for _ in range(5)]
        service_compute._active_invocations = set(invocation_ids)

        # Act
        health = service_compute.get_service_health()

        # Assert
        assert health["active_invocations"] == 5
        assert len(service_compute._active_invocations) == 5

    def test_get_service_health_success_rate(self, service_compute):
        """Test success rate calculation with various scenarios."""
        # Scenario 1: Perfect success rate
        service_compute._total_invocations = 100
        service_compute._successful_invocations = 100
        service_compute._failed_invocations = 0

        health = service_compute.get_service_health()
        assert health["success_rate"] == 1.0

        # Scenario 2: 80% success rate
        service_compute._total_invocations = 100
        service_compute._successful_invocations = 80
        service_compute._failed_invocations = 20

        health = service_compute.get_service_health()
        assert health["success_rate"] == 0.8

        # Scenario 3: 0% success rate
        service_compute._total_invocations = 50
        service_compute._successful_invocations = 0
        service_compute._failed_invocations = 50

        health = service_compute.get_service_health()
        assert health["success_rate"] == 0.0

        # Scenario 4: Zero invocations (default to 1.0)
        service_compute._total_invocations = 0
        service_compute._successful_invocations = 0
        service_compute._failed_invocations = 0

        health = service_compute.get_service_health()
        assert health["success_rate"] == 1.0


class TestModelServiceComputeHealthMonitoring:
    """Test cases for health monitoring loop."""

    @pytest.mark.asyncio
    async def test_health_monitor_loop_runs_while_active(self, service_compute):
        """Test health monitoring loop runs during service lifetime."""
        # Arrange
        service_compute._service_running = True
        service_compute._shutdown_requested = False
        check_count = 0

        # Mock get_service_health to count calls
        original_get_health = service_compute.get_service_health

        def counting_get_health():
            nonlocal check_count
            check_count += 1
            return original_get_health()

        service_compute.get_service_health = counting_get_health

        # Mock asyncio.sleep to speed up test
        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)
            # Stop after 3 iterations
            if len(sleep_calls) >= 3:
                service_compute._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_compute._health_monitor_loop()

        # Assert
        assert check_count == 3
        assert len(sleep_calls) == 3
        assert all(s == 30 for s in sleep_calls)  # 30 second intervals

    @pytest.mark.asyncio
    async def test_health_monitor_loop_logs_periodically(self, service_compute):
        """Test periodic health logging every 100 invocations."""
        # Arrange
        service_compute._service_running = True
        service_compute._shutdown_requested = False
        log_messages = []

        # Mock logging to capture messages
        def mock_log_info(message):
            log_messages.append(message)

        service_compute._log_info = mock_log_info

        # Mock asyncio.sleep
        async def mock_sleep(seconds):
            # Simulate invocations
            if service_compute._total_invocations == 0:
                service_compute._total_invocations = 100
                service_compute._successful_invocations = 95
            else:
                service_compute._shutdown_requested = True

        # Act
        with patch("asyncio.sleep", mock_sleep):
            await service_compute._health_monitor_loop()

        # Assert
        health_logs = [msg for msg in log_messages if "Health:" in msg]
        assert len(health_logs) > 0
        assert "active" in health_logs[0]
        assert "success rate" in health_logs[0]

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_cancellation(self, service_compute):
        """Test health monitor loop handles CancelledError gracefully."""
        # Arrange
        service_compute._service_running = True
        service_compute._shutdown_requested = False
        log_messages = []

        def mock_log_info(message):
            log_messages.append(message)

        service_compute._log_info = mock_log_info

        # Mock asyncio.sleep to raise CancelledError
        async def mock_sleep(seconds):
            raise asyncio.CancelledError

        # Act
        with patch("asyncio.sleep", mock_sleep):
            with pytest.raises(asyncio.CancelledError):
                await service_compute._health_monitor_loop()

        # Assert - CancelledError should be re-raised immediately without logging
        # to prevent "I/O operation on closed file" errors during teardown
        cancel_logs = [msg for msg in log_messages if "cancelled" in msg.lower()]
        assert (
            len(cancel_logs) == 0
        ), "Should not log during cancellation to avoid closed file errors"

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_exceptions(self, service_compute):
        """Test health monitor loop logs exceptions without propagating."""
        # Arrange
        service_compute._service_running = True
        service_compute._shutdown_requested = False
        error_logs = []

        def mock_log_error(message):
            error_logs.append(message)

        service_compute._log_error = mock_log_error

        # Mock get_service_health to raise exception
        def failing_get_health():
            raise RuntimeError("Health check failed")

        service_compute.get_service_health = failing_get_health

        # Act
        await service_compute._health_monitor_loop()

        # Assert
        assert len(error_logs) == 1
        assert "Health monitor error" in error_logs[0]
        assert "Health check failed" in error_logs[0]


class TestModelServiceComputeGracefulShutdown:
    """Test cases for graceful shutdown."""

    @pytest.mark.asyncio
    async def test_stop_service_mode_basic(self, service_compute, mock_event_bus):
        """Test basic graceful shutdown."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        service_compute._health_task = asyncio.create_task(asyncio.sleep(10))

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_compute._wait_for_active_invocations = mock_wait

        # Act
        await service_compute.stop_service_mode()

        # Assert
        assert service_compute._service_running is False
        assert service_compute._shutdown_requested is True
        assert service_compute._health_task.cancelled()

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_timeout(self, service_compute):
        """Test timeout with active invocations remaining."""
        # Arrange
        invocation_ids = [uuid4() for _ in range(3)]
        service_compute._active_invocations = set(invocation_ids)
        warning_logs = []

        def mock_log_warning(message):
            warning_logs.append(message)

        service_compute._log_warning = mock_log_warning

        # Act
        with patch("time.time") as mock_time:
            # Simulate timeout
            mock_time.side_effect = [0, 0.1, 0.2, 31.0]  # Exceeds 30s timeout
            await service_compute._wait_for_active_invocations(timeout_ms=30000)

        # Assert
        assert len(warning_logs) == 1
        assert "Timeout waiting for invocations" in warning_logs[0]
        assert "3 still active" in warning_logs[0]

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_success(self, service_compute, mock_event_bus):
        """Test shutdown event emission."""
        # Act
        await service_compute._emit_shutdown_event()

        # Assert
        mock_event_bus.publish.assert_called_once()
        call_args = mock_event_bus.publish.call_args[0]
        assert isinstance(call_args[0], ModelNodeShutdownEvent)
        # Use node_id (aliased to _node_id) for comparison
        assert call_args[0].node_id == service_compute.node_id
        assert call_args[0].shutdown_reason == "graceful"

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_executed(self, service_compute):
        """Test callbacks executed on shutdown."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        callback_results = []

        def callback1():
            callback_results.append("callback1")

        def callback2():
            callback_results.append("callback2")

        def callback3():
            callback_results.append("callback3")

        service_compute.add_shutdown_callback(callback1)
        service_compute.add_shutdown_callback(callback2)
        service_compute.add_shutdown_callback(callback3)

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_compute._wait_for_active_invocations = mock_wait

        # Act
        await service_compute.stop_service_mode()

        # Assert
        assert len(callback_results) == 3
        assert callback_results == ["callback1", "callback2", "callback3"]

    @pytest.mark.asyncio
    async def test_shutdown_callback_exception_handling(self, service_compute):
        """Test exception in callback doesn't stop other callbacks."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        callback_results = []
        error_logs = []

        def mock_log_error(message):
            error_logs.append(message)

        service_compute._log_error = mock_log_error

        def good_callback1():
            callback_results.append("good1")

        def failing_callback():
            raise RuntimeError("Callback failed")

        def good_callback2():
            callback_results.append("good2")

        service_compute.add_shutdown_callback(good_callback1)
        service_compute.add_shutdown_callback(failing_callback)
        service_compute.add_shutdown_callback(good_callback2)

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_compute._wait_for_active_invocations = mock_wait

        # Act
        await service_compute.stop_service_mode()

        # Assert
        assert len(callback_results) == 2
        assert callback_results == ["good1", "good2"]
        assert len(error_logs) == 1
        assert "Shutdown callback failed" in error_logs[0]

    def test_register_signal_handlers_success(self, service_compute):
        """Test signal handlers registered correctly."""
        # Arrange
        original_sigterm = signal.getsignal(signal.SIGTERM)
        original_sigint = signal.getsignal(signal.SIGINT)

        # Act
        service_compute._register_signal_handlers()

        # Assert
        # Signal handlers should be changed
        assert signal.getsignal(signal.SIGTERM) != original_sigterm
        assert signal.getsignal(signal.SIGINT) != original_sigint

        # Restore original handlers
        signal.signal(signal.SIGTERM, original_sigterm)
        signal.signal(signal.SIGINT, original_sigint)

    def test_signal_handler_sets_shutdown_flag(self, service_compute):
        """Test signal handler behavior sets shutdown flag."""
        # Arrange
        service_compute._shutdown_requested = False
        log_messages = []

        def mock_log_info(message):
            log_messages.append(message)

        service_compute._log_info = mock_log_info

        original_sigterm = signal.getsignal(signal.SIGTERM)

        try:
            # Act
            service_compute._register_signal_handlers()

            # Get the registered handler
            handler = signal.getsignal(signal.SIGTERM)

            # Simulate signal
            handler(signal.SIGTERM, None)

            # Assert
            assert service_compute._shutdown_requested is True
            assert any("signal" in msg.lower() for msg in log_messages)

        finally:
            # Restore original handler
            signal.signal(signal.SIGTERM, original_sigterm)

    @pytest.mark.asyncio
    async def test_shutdown_during_active_invocations(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """Test shutdown waits for active invocations to complete."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        invocation_started = asyncio.Event()
        invocation_completed = asyncio.Event()

        # Mock long-running invocation
        async def slow_run(input_state):
            invocation_started.set()
            await asyncio.sleep(0.15)
            invocation_completed.set()
            return {"result": "success"}

        service_compute.run = slow_run

        # Start invocation in background
        invocation_task = asyncio.create_task(
            service_compute.handle_tool_invocation(tool_invocation_event)
        )

        # Wait for invocation to actually start
        await asyncio.wait_for(invocation_started.wait(), timeout=1.0)

        # Verify invocation is active
        assert len(service_compute._active_invocations) == 1

        # Act - stop service while invocation is active
        stop_task = asyncio.create_task(service_compute.stop_service_mode())

        # Wait for both to complete
        await asyncio.gather(invocation_task, stop_task)

        # Assert
        assert invocation_completed.is_set() is True
        assert service_compute._service_running is False
        assert len(service_compute._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_stop_service_mode_cancels_health_task(self, service_compute):
        """Test health task is cancelled during shutdown."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()

        # Create a health task
        async def long_health_check():
            await asyncio.sleep(10)

        service_compute._health_task = asyncio.create_task(long_health_check())

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_compute._wait_for_active_invocations = mock_wait

        # Act
        await service_compute.stop_service_mode()

        # Assert
        assert service_compute._health_task.cancelled()

    @pytest.mark.asyncio
    async def test_stop_service_mode_cleanup_event_handlers(self, service_compute):
        """Test cleanup_event_handlers is called during shutdown."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        cleanup_called = False

        def mock_cleanup():
            nonlocal cleanup_called
            cleanup_called = True

        service_compute.cleanup_event_handlers = mock_cleanup

        # Mock wait for invocations
        async def mock_wait(timeout_ms):
            pass

        service_compute._wait_for_active_invocations = mock_wait

        # Act
        await service_compute.stop_service_mode()

        # Assert
        assert cleanup_called is True


class TestModelServiceComputeHealthEdgeCases:
    """Test edge cases for health monitoring and shutdown."""

    def test_get_service_health_before_start(self, service_compute):
        """Test health status before service started."""
        # Arrange
        service_compute._service_running = False
        service_compute._start_time = None

        # Act
        health = service_compute.get_service_health()

        # Assert
        assert health["status"] == "unhealthy"
        assert health["uptime_seconds"] == 0

    def test_get_service_health_status_unhealthy_when_shutdown_requested(
        self, service_compute
    ):
        """Test status is unhealthy when shutdown requested."""
        # Arrange
        service_compute._service_running = True
        service_compute._start_time = time.time()
        service_compute._shutdown_requested = True

        # Act
        health = service_compute.get_service_health()

        # Assert
        assert health["status"] == "unhealthy"
        assert health["shutdown_requested"] is True

    @pytest.mark.asyncio
    async def test_stop_service_mode_idempotent(self, service_compute):
        """Test stopping already stopped service is safe."""
        # Arrange
        service_compute._service_running = False

        # Act - stop should return immediately
        await service_compute.stop_service_mode()

        # Assert - no exceptions raised
        assert service_compute._service_running is False

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_none(self, service_compute):
        """Test waiting with no active invocations returns immediately."""
        # Arrange
        service_compute._active_invocations = set()

        # Act
        start = time.time()
        await service_compute._wait_for_active_invocations(timeout_ms=30000)
        elapsed = time.time() - start

        # Assert - should return almost immediately
        assert elapsed < 0.1
        assert len(service_compute._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_completes_in_time(self, service_compute):
        """Test waiting for invocations that complete before timeout."""
        # Arrange
        invocation_id = uuid4()
        service_compute._active_invocations = {invocation_id}

        # Simulate invocation completing
        async def complete_invocation():
            await asyncio.sleep(0.1)
            service_compute._active_invocations.discard(invocation_id)

        # Act
        complete_task = asyncio.create_task(complete_invocation())
        wait_task = asyncio.create_task(
            service_compute._wait_for_active_invocations(timeout_ms=5000)
        )

        await asyncio.gather(complete_task, wait_task)

        # Assert
        assert len(service_compute._active_invocations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
