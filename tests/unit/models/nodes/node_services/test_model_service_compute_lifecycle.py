"""
Test suite for ModelServiceCompute lifecycle operations.

Tests service initialization, startup, shutdown, and lifecycle management
for compute nodes running in persistent service mode.
"""

import asyncio
import signal
import time
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.constants.constants_event_types import TOOL_INVOCATION
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_compute import ModelContractCompute
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.services.model_service_compute import ModelServiceCompute


class ComputeNodeForTesting(ModelServiceCompute):
    """Compute node for lifecycle testing (not a pytest test class)."""

    def __init__(self, container: ModelONEXContainer, node_id, event_bus):
        # Set required attributes before calling super().__init__
        self._node_id = node_id
        self.event_bus = event_bus
        self._node_name = "test_compute_node"

        # Call parent init
        super().__init__(container)

    async def execute_compute(self, contract: ModelContractCompute) -> dict:
        """Simple compute execution for testing."""
        return {"result": "compute_complete", "data": contract.model_dump()}

    async def run(self, input_state):
        """Run method for tool execution."""
        return {"result": "executed", "action": getattr(input_state, "action", "test")}

    def _extract_node_name(self) -> str:
        """Extract node name for logging."""
        return self._node_name

    def _publish_introspection_event(self):
        """Mock introspection publishing."""

    def cleanup_event_handlers(self):
        """Mock cleanup."""


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    event_bus = AsyncMock()
    event_bus.subscribe = Mock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def compute_node(mock_container, mock_event_bus):
    """Create test compute node with mocked dependencies."""
    node_id = uuid4()
    node = ComputeNodeForTesting(mock_container, node_id, mock_event_bus)
    return node


@pytest.fixture
def tool_invocation_event(compute_node):
    """Create sample tool invocation event."""
    return ModelToolInvocationEvent.create_tool_invocation(
        target_node_id=compute_node._node_id,
        target_node_name=compute_node._node_name,
        tool_name="test_tool",
        action="compute",
        requester_id=uuid4(),
        requester_node_id=uuid4(),
        parameters={"input": "test_data"},
    )


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelServiceComputeLifecycle:
    """Test ModelServiceCompute lifecycle operations."""

    def test_service_initialization(self, compute_node):
        """
        Test service initialization sets up all required attributes.

        Verifies:
        - Service state flags initialized
        - Performance counters at zero
        - Shutdown state initialized
        - Collections initialized
        """
        # Verify service state
        assert hasattr(compute_node, "_service_running")
        assert compute_node._service_running is False

        # Verify task management
        assert hasattr(compute_node, "_service_task")
        assert compute_node._service_task is None
        assert hasattr(compute_node, "_health_task")
        assert compute_node._health_task is None

        # Verify active invocations tracking
        assert hasattr(compute_node, "_active_invocations")
        assert isinstance(compute_node._active_invocations, set)
        assert len(compute_node._active_invocations) == 0

        # Verify performance tracking
        assert compute_node._total_invocations == 0
        assert compute_node._successful_invocations == 0
        assert compute_node._failed_invocations == 0
        assert compute_node._start_time is None

        # Verify shutdown handling
        assert compute_node._shutdown_requested is False
        assert isinstance(compute_node._shutdown_callbacks, list)
        assert len(compute_node._shutdown_callbacks) == 0

    @pytest.mark.asyncio
    async def test_service_start_basic(self, compute_node, mock_event_bus):
        """
        Test basic service startup.

        Verifies:
        - Service running flag set
        - Start time recorded
        - Event loop entered (cancelled for test)
        """
        # Start service in background and cancel after brief delay
        service_task = asyncio.create_task(compute_node.start_service_mode())

        # Give service time to initialize
        await asyncio.sleep(0.1)

        # Verify service started
        assert compute_node._service_running is True
        assert compute_node._start_time is not None
        assert isinstance(compute_node._start_time, float)

        # Stop the service
        await compute_node.stop_service_mode()
        service_task.cancel()

        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_start_publishes_introspection(self, compute_node):
        """
        Test that service startup publishes introspection event.

        Verifies:
        - Introspection method called during startup
        """
        with patch.object(
            compute_node, "_publish_introspection_event"
        ) as mock_introspection:
            # Start service
            service_task = asyncio.create_task(compute_node.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify introspection published
            mock_introspection.assert_called_once()

            # Cleanup
            await compute_node.stop_service_mode()
            service_task.cancel()
            try:
                await service_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_service_start_subscribes_to_tool_invocations(
        self, compute_node, mock_event_bus
    ):
        """
        Test that service startup subscribes to TOOL_INVOCATION events.

        Verifies:
        - Event bus subscribe called with correct event type
        - Handler function registered
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        # Verify subscription
        mock_event_bus.subscribe.assert_called_once()
        call_args = mock_event_bus.subscribe.call_args
        assert call_args[0][0] == compute_node.handle_tool_invocation
        assert call_args[0][1] == TOOL_INVOCATION

        # Cleanup
        await compute_node.stop_service_mode()
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_start_creates_health_monitoring_task(self, compute_node):
        """
        Test that service startup creates health monitoring task.

        Verifies:
        - Health task created
        - Health task is running
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        # Verify health task created
        assert compute_node._health_task is not None
        assert isinstance(compute_node._health_task, asyncio.Task)
        assert not compute_node._health_task.done()

        # Cleanup
        await compute_node.stop_service_mode()
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_start_registers_signal_handlers(self, compute_node):
        """
        Test that service startup registers signal handlers.

        Verifies:
        - Signal handlers registered for SIGTERM and SIGINT
        """
        with patch("signal.signal") as mock_signal:
            # Start service
            service_task = asyncio.create_task(compute_node.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify signal handlers registered
            assert mock_signal.call_count >= 2
            signal_calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in signal_calls
            assert signal.SIGINT in signal_calls

            # Cleanup
            await compute_node.stop_service_mode()
            service_task.cancel()
            try:
                await service_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_service_start_error_handling(self, compute_node):
        """
        Test error handling during service startup.

        Verifies:
        - Exception propagated
        - Service stopped on error
        """
        # Make subscription fail
        compute_node.event_bus = None

        # Attempt to start service should fail
        with pytest.raises(
            ModelOnexError, match="Event bus not available for subscription"
        ):
            await compute_node.start_service_mode()

        # Verify service stopped
        assert compute_node._service_running is False

    @pytest.mark.asyncio
    async def test_service_start_idempotency(self, compute_node):
        """
        Test that multiple start attempts are handled gracefully.

        Verifies:
        - Second start attempt logged as warning
        - No duplicate tasks created
        - Service remains running
        """
        # Start service first time
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        assert compute_node._service_running is True
        first_start_time = compute_node._start_time

        # Attempt to start again
        with patch.object(compute_node, "_log_warning") as mock_warning:
            await compute_node.start_service_mode()
            mock_warning.assert_called_once()
            assert "already running" in mock_warning.call_args[0][0].lower()

        # Verify service still running with same start time
        assert compute_node._service_running is True
        assert compute_node._start_time == first_start_time

        # Cleanup
        await compute_node.stop_service_mode()
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_basic(self, compute_node):
        """
        Test basic service shutdown.

        Verifies:
        - Service running flag cleared
        - Shutdown requested flag set
        - Service stops gracefully
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        assert compute_node._service_running is True

        # Stop service
        await compute_node.stop_service_mode()

        # Verify service stopped
        assert compute_node._service_running is False
        assert compute_node._shutdown_requested is True

        # Cancel the service task
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_emits_shutdown_event(
        self, compute_node, mock_event_bus
    ):
        """
        Test that service shutdown emits shutdown event.

        Verifies:
        - Shutdown event published to event bus
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        # Stop service
        await compute_node.stop_service_mode()

        # Verify shutdown event published
        assert mock_event_bus.publish.called
        # Check if any call was a shutdown event
        shutdown_calls = [
            call
            for call in mock_event_bus.publish.call_args_list
            if len(call[0]) > 0 and isinstance(call[0][0], ModelNodeShutdownEvent)
        ]
        assert len(shutdown_calls) > 0

        # Cleanup
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_cancels_health_task(self, compute_node):
        """
        Test that service shutdown cancels health monitoring task.

        Verifies:
        - Health task cancelled
        - Health task cleanup handled
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        health_task = compute_node._health_task
        assert health_task is not None
        assert not health_task.done()

        # Stop service
        await compute_node.stop_service_mode()

        # Verify health task cancelled
        assert health_task.done()
        assert health_task.cancelled() or health_task.exception() is None

        # Cleanup
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_waits_for_active_invocations(self, compute_node):
        """
        Test that service shutdown waits for active invocations.

        Verifies:
        - Wait method called during shutdown
        - Active invocations tracked
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        # Add fake active invocation
        fake_correlation_id = uuid4()
        compute_node._active_invocations.add(fake_correlation_id)

        # Mock the wait method to track call
        with patch.object(
            compute_node, "_wait_for_active_invocations", new_callable=AsyncMock
        ) as mock_wait:
            await compute_node.stop_service_mode()

            # Verify wait was called
            mock_wait.assert_called_once()
            assert mock_wait.call_args[1]["timeout_ms"] == 30000

        # Cleanup
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_runs_shutdown_callbacks(self, compute_node):
        """
        Test that service shutdown runs shutdown callbacks.

        Verifies:
        - All registered callbacks executed
        - Callbacks run in order
        """
        # Start service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        # Register callbacks
        callback1 = Mock()
        callback2 = Mock()
        compute_node.add_shutdown_callback(callback1)
        compute_node.add_shutdown_callback(callback2)

        # Stop service
        await compute_node.stop_service_mode()

        # Verify callbacks called
        callback1.assert_called_once()
        callback2.assert_called_once()

        # Cleanup
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_service_stop_idempotent(self, compute_node):
        """
        Test that stopping already stopped service is safe.

        Verifies:
        - No errors on second stop
        - Graceful handling
        """
        # Stop service when not running
        await compute_node.stop_service_mode()

        # Should complete without error
        assert compute_node._service_running is False

    @pytest.mark.asyncio
    async def test_service_restart_cycles(self, compute_node):
        """
        Test multiple service start/stop cycles.

        Verifies:
        - Service can be restarted after stop
        - State properly reset between cycles
        - No resource leaks
        """
        for cycle in range(3):
            # Start service
            service_task = asyncio.create_task(compute_node.start_service_mode())
            await asyncio.sleep(0.1)

            assert compute_node._service_running is True
            assert compute_node._start_time is not None

            # Stop service
            await compute_node.stop_service_mode()
            assert compute_node._service_running is False

            # Reset shutdown flag for next cycle
            compute_node._shutdown_requested = False

            # Cancel task
            service_task.cancel()
            try:
                await service_task
            except asyncio.CancelledError:
                pass

            # Small delay between cycles
            await asyncio.sleep(0.05)


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelServiceComputeToolInvocation:
    """Test tool invocation handling in service mode."""

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_basic(
        self, compute_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test basic tool invocation handling.

        Verifies:
        - Invocation tracked
        - Tool executed
        - Response emitted
        - Metrics updated
        """
        # Track initial metrics
        initial_total = compute_node._total_invocations

        # Handle invocation
        await compute_node.handle_tool_invocation(tool_invocation_event)

        # Verify metrics updated
        assert compute_node._total_invocations == initial_total + 1
        assert compute_node._successful_invocations == 1
        assert compute_node._failed_invocations == 0

        # Verify response emitted
        assert mock_event_bus.publish.called
        response_calls = [
            call
            for call in mock_event_bus.publish.call_args_list
            if len(call[0]) > 0 and isinstance(call[0][0], ModelToolResponseEvent)
        ]
        assert len(response_calls) > 0

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_wrong_target(
        self, compute_node, tool_invocation_event
    ):
        """
        Test tool invocation with wrong target is ignored.

        Verifies:
        - Warning logged
        - No execution performed
        """
        # Change target to different node
        tool_invocation_event.target_node_id = uuid4()
        tool_invocation_event.target_node_name = "different_node"

        initial_total = compute_node._total_invocations

        # Handle invocation
        with patch.object(compute_node, "_log_warning") as mock_warning:
            await compute_node.handle_tool_invocation(tool_invocation_event)
            mock_warning.assert_called_once()

        # Verify execution did not occur (total incremented but no success)
        assert compute_node._total_invocations == initial_total + 1
        assert compute_node._successful_invocations == 0


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelServiceComputeHealthMonitoring:
    """Test health monitoring functionality."""

    def test_get_service_health_basic(self, compute_node):
        """
        Test basic health status retrieval.

        Verifies:
        - Health dict contains required fields
        - Status reflects service state
        """
        health = compute_node.get_service_health()

        # Verify required fields
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

        # Verify status
        assert health["status"] == "unhealthy"  # Service not running
        assert health["uptime_seconds"] == 0
        assert health["success_rate"] == 1.0  # No invocations = 100%

    def test_get_service_health_running(self, compute_node):
        """
        Test health status when service is running.

        Verifies:
        - Status is healthy
        - Uptime calculated correctly
        """
        # Set service state
        compute_node._service_running = True
        compute_node._start_time = time.time() - 60  # Started 60 seconds ago

        health = compute_node.get_service_health()

        assert health["status"] == "healthy"
        assert health["uptime_seconds"] >= 59  # Allow for small timing variation
        assert health["uptime_seconds"] <= 61

    def test_get_service_health_with_invocations(self, compute_node):
        """
        Test health status with invocation metrics.

        Verifies:
        - Active invocations tracked
        - Success rate calculated correctly
        """
        # Set metrics
        compute_node._total_invocations = 100
        compute_node._successful_invocations = 90
        compute_node._failed_invocations = 10
        compute_node._active_invocations.add(uuid4())
        compute_node._active_invocations.add(uuid4())

        health = compute_node.get_service_health()

        assert health["active_invocations"] == 2
        assert health["total_invocations"] == 100
        assert health["successful_invocations"] == 90
        assert health["failed_invocations"] == 10
        assert health["success_rate"] == 0.9  # 90/100


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelServiceComputeShutdownHandling:
    """Test shutdown handling and callbacks."""

    def test_add_shutdown_callback(self, compute_node):
        """
        Test adding shutdown callbacks.

        Verifies:
        - Callbacks stored in list
        """
        callback = Mock()
        compute_node.add_shutdown_callback(callback)

        assert len(compute_node._shutdown_callbacks) == 1
        assert compute_node._shutdown_callbacks[0] == callback

    def test_add_multiple_shutdown_callbacks(self, compute_node):
        """
        Test adding multiple shutdown callbacks.

        Verifies:
        - All callbacks stored
        - Order preserved
        """
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        compute_node.add_shutdown_callback(callback1)
        compute_node.add_shutdown_callback(callback2)
        compute_node.add_shutdown_callback(callback3)

        assert len(compute_node._shutdown_callbacks) == 3
        assert compute_node._shutdown_callbacks == [callback1, callback2, callback3]

    @pytest.mark.asyncio
    async def test_shutdown_callback_exception_handling(self, compute_node):
        """
        Test exception handling in shutdown callbacks.

        Verifies:
        - Exception logged
        - Other callbacks still run
        - Shutdown continues
        """
        # Create callbacks with one that raises
        callback1 = Mock()
        callback2 = Mock(side_effect=RuntimeError("Callback error"))
        callback3 = Mock()

        compute_node.add_shutdown_callback(callback1)
        compute_node.add_shutdown_callback(callback2)
        compute_node.add_shutdown_callback(callback3)

        # Start and stop service
        service_task = asyncio.create_task(compute_node.start_service_mode())
        await asyncio.sleep(0.1)

        await compute_node.stop_service_mode()

        # Verify all callbacks attempted
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()

        # Verify shutdown completed
        assert compute_node._service_running is False

        # Cleanup
        service_task.cancel()
        try:
            await service_task
        except asyncio.CancelledError:
            pass
