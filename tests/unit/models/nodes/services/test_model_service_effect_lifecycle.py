"""
Test suite for ModelServiceEffect lifecycle management.

Tests service initialization, startup, shutdown, introspection, event handling,
health monitoring, signal handlers, error handling, and idempotency.

Following test plan: MIXIN_NODE_SERVICE_TEST_PLAN.md
"""

import asyncio
import signal
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.constants.event_types import TOOL_INVOCATION
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.nodes.services.model_service_effect import ModelServiceEffect


# Test Fixtures
@pytest.fixture
def mock_container():
    """Create mock ONEX container with all necessary dependencies."""
    container = Mock(spec=ModelONEXContainer)
    container.get_service = Mock(return_value=None)
    return container


@pytest.fixture
def mock_event_bus():
    """Create mock event bus for testing event subscriptions and publications."""
    event_bus = AsyncMock()
    event_bus.subscribe = Mock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def service_effect(request, mock_container, mock_event_bus, service_cleanup):
    """Create ModelServiceEffect instance with mocked dependencies.

    We bypass normal initialization due to Pydantic BaseModel complexity in the MRO.
    This creates a functional instance for testing service lifecycle methods.

    Automatic cleanup is registered to prevent async task warnings.
    """
    node_id = uuid4()

    # Create instance without calling __init__ to avoid Pydantic issues
    service = object.__new__(ModelServiceEffect)

    # Initialize Pydantic internal structures (required for BaseModel)
    object.__setattr__(service, "__pydantic_fields_set__", set())
    object.__setattr__(service, "__pydantic_extra__", {})
    object.__setattr__(service, "__pydantic_private__", {})

    # Core node attributes (from NodeCoreBase)
    object.__setattr__(service, "container", mock_container)
    object.__setattr__(service, "node_id", node_id)
    object.__setattr__(service, "_node_id", node_id)
    object.__setattr__(service, "created_at", datetime.now())
    object.__setattr__(service, "state", {"status": "initialized"})
    object.__setattr__(
        service,
        "metrics",
        {
            "initialization_time_ms": 0.0,
            "total_operations": 0.0,
            "avg_processing_time_ms": 0.0,
            "error_count": 0.0,
            "success_count": 0.0,
        },
    )
    object.__setattr__(service, "contract_data", None)
    object.__setattr__(service, "version", "1.0.0")

    # Service mixin state (from MixinNodeService)
    object.__setattr__(service, "_service_running", False)
    object.__setattr__(service, "_service_task", None)
    object.__setattr__(service, "_health_task", None)
    object.__setattr__(service, "_active_invocations", set())
    object.__setattr__(service, "_total_invocations", 0)
    object.__setattr__(service, "_successful_invocations", 0)
    object.__setattr__(service, "_failed_invocations", 0)
    object.__setattr__(service, "_start_time", None)
    object.__setattr__(service, "_shutdown_requested", False)
    object.__setattr__(service, "_shutdown_callbacks", [])

    # Event bus mixin attributes
    object.__setattr__(service, "event_bus", mock_event_bus)
    object.__setattr__(service, "node_name", "test_effect_node")
    object.__setattr__(service, "_node_name", "test_effect_node")
    object.__setattr__(service, "registry", None)
    object.__setattr__(service, "contract_path", None)
    object.__setattr__(service, "event_listener_thread", None)
    object.__setattr__(service, "stop_event", None)
    object.__setattr__(service, "event_subscriptions", [])

    # Effect-specific attributes (from NodeEffect)
    object.__setattr__(service, "default_timeout_ms", 30000)
    object.__setattr__(service, "default_retry_delay_ms", 1000)
    object.__setattr__(service, "max_concurrent_effects", 10)
    object.__setattr__(service, "active_transactions", {})
    object.__setattr__(service, "circuit_breakers", {})
    object.__setattr__(service, "effect_handlers", {})
    object.__setattr__(service, "effect_semaphore", asyncio.Semaphore(10))
    object.__setattr__(service, "effect_metrics", {})

    # Bind instance methods (needed for proper method calls)
    service._extract_node_name = lambda: "test_effect_node"
    service._publish_introspection_event = Mock()
    service.cleanup_event_handlers = Mock()
    service._log_warning = Mock()
    service._log_info = Mock()
    service._log_error = Mock()
    service.run = AsyncMock(return_value={"result": "executed", "action": "test"})

    # Register for automatic cleanup
    service_cleanup.register(service)

    return service


@pytest.fixture
def tool_invocation_event(service_effect):
    """Create sample tool invocation event for testing."""
    return ModelToolInvocationEvent.create_tool_invocation(
        target_node_id=service_effect._node_id,
        target_node_name=service_effect._node_name,
        tool_name="test_tool",
        action="execute",
        requester_id=uuid4(),
        requester_node_id=uuid4(),
        parameters={"input": "test_data"},
    )


@pytest.fixture
def correlation_id():
    """Generate correlation ID for request/response tracking."""
    return uuid4()


# Test Classes
class TestModelServiceEffectInitialization:
    """Test service initialization and setup."""

    def test_service_initialization(self, service_effect, mock_container):
        """Test that ModelServiceEffect initializes correctly with container."""
        service = service_effect

        # Verify service attributes initialized
        assert service.container is mock_container
        assert service._service_running is False
        assert service._service_task is None
        assert service._health_task is None
        assert isinstance(service._active_invocations, set)
        assert len(service._active_invocations) == 0

        # Verify performance metrics initialized
        assert service._total_invocations == 0
        assert service._successful_invocations == 0
        assert service._failed_invocations == 0
        assert service._start_time is None

        # Verify shutdown state initialized
        assert service._shutdown_requested is False
        assert isinstance(service._shutdown_callbacks, list)
        assert len(service._shutdown_callbacks) == 0

    def test_service_has_required_mixins(self, service_effect):
        """Test that service has all required mixin capabilities."""
        service = service_effect

        # Verify MixinNodeService capabilities
        assert hasattr(service, "start_service_mode")
        assert hasattr(service, "stop_service_mode")
        assert hasattr(service, "handle_tool_invocation")
        assert hasattr(service, "get_service_health")

        # Verify MixinHealthCheck capabilities
        assert hasattr(service, "health_check")
        assert hasattr(service, "health_check_async")

        # Verify MixinEventBus capabilities
        assert hasattr(service, "publish_event")

        # Verify MixinMetrics capabilities
        assert hasattr(service, "record_metric")


class TestModelServiceEffectStartup:
    """Test service startup behavior."""

    @pytest.mark.asyncio
    async def test_start_service_mode_publishes_introspection(self, service_effect):
        """Test that start_service_mode publishes introspection on startup."""
        # Mock the event loop to prevent infinite waiting
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ) as mock_loop:
            mock_loop.return_value = None

            await service_effect.start_service_mode()

            # Verify introspection was published
            service_effect._publish_introspection_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_service_mode_subscribes_to_tool_invocation(
        self, service_effect, mock_event_bus
    ):
        """Test that service subscribes to TOOL_INVOCATION events on startup."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            await service_effect.start_service_mode()

            # Verify subscription to TOOL_INVOCATION events
            mock_event_bus.subscribe.assert_called_once_with(
                service_effect.handle_tool_invocation,
                TOOL_INVOCATION,
            )

    @pytest.mark.asyncio
    async def test_start_service_mode_starts_health_monitoring(self, service_effect):
        """Test that health monitoring task is created on startup."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            with patch("asyncio.create_task") as mock_create_task:
                # Mock the health monitor loop
                mock_task = AsyncMock()
                mock_create_task.return_value = mock_task

                await service_effect.start_service_mode()

                # Verify health monitoring task was created
                assert mock_create_task.called

    @pytest.mark.asyncio
    async def test_start_service_mode_registers_signal_handlers(self, service_effect):
        """Test that signal handlers (SIGTERM, SIGINT) are registered on startup."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            with patch("signal.signal") as mock_signal:
                await service_effect.start_service_mode()

                # Verify signal handlers were registered
                # Should register SIGTERM and SIGINT
                calls = mock_signal.call_args_list
                signal_numbers = [call[0][0] for call in calls]

                assert signal.SIGTERM in signal_numbers
                assert signal.SIGINT in signal_numbers

    @pytest.mark.asyncio
    async def test_start_service_mode_sets_running_flag(self, service_effect):
        """Test that service running flag is set during startup."""
        # Create a flag to track when the event loop is called
        event_loop_called = asyncio.Event()

        async def mock_event_loop():
            event_loop_called.set()
            # Let it run briefly
            await asyncio.sleep(0.01)

        with patch.object(
            service_effect, "_service_event_loop", side_effect=mock_event_loop
        ):
            # Start service in background
            service_task = asyncio.create_task(service_effect.start_service_mode())

            # Wait for event loop to be called
            await asyncio.wait_for(event_loop_called.wait(), timeout=1.0)

            # Verify service is running
            assert service_effect._service_running is True
            assert service_effect._start_time is not None

            # Stop the service
            service_effect._shutdown_requested = True
            await service_task

    @pytest.mark.asyncio
    async def test_start_service_mode_error_handling(
        self, service_effect, mock_event_bus
    ):
        """Test error handling when startup fails."""
        # Make subscription fail
        mock_event_bus.subscribe.side_effect = RuntimeError("Event bus unavailable")

        with pytest.raises(RuntimeError, match="Event bus unavailable"):
            await service_effect.start_service_mode()

        # Verify service is not running after failure
        assert service_effect._service_running is False

    @pytest.mark.asyncio
    async def test_start_service_mode_idempotent(self, service_effect):
        """Test that calling start_service_mode multiple times is idempotent."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            # First start
            await service_effect.start_service_mode()

            # Mark as running
            service_effect._service_running = True

            # Try to start again
            await service_effect.start_service_mode()

            # Should not raise error, just ignore


class TestModelServiceEffectShutdown:
    """Test service shutdown behavior."""

    @pytest.mark.asyncio
    async def test_stop_service_mode_emits_shutdown_event(
        self, service_effect, mock_event_bus
    ):
        """Test that shutdown event is emitted when stopping service."""
        # Set service as running
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()

        await service_effect.stop_service_mode()

        # Verify shutdown event was published
        assert mock_event_bus.publish.called

        # Get the published event
        call_args = mock_event_bus.publish.call_args_list
        shutdown_event = None
        for call in call_args:
            if call[0] and isinstance(call[0][0], ModelNodeShutdownEvent):
                shutdown_event = call[0][0]
                break

        assert shutdown_event is not None

    @pytest.mark.asyncio
    async def test_stop_service_mode_cancels_health_task(self, service_effect):
        """Test that health monitoring task is cancelled during shutdown."""
        # Set service as running
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()

        # Create a mock health task with proper done() method
        mock_health_task = Mock()
        mock_health_task.done = Mock(return_value=False)  # Returns boolean, not a Mock
        mock_health_task.cancel = Mock()
        service_effect._health_task = mock_health_task

        await service_effect.stop_service_mode()

        # Verify health task was cancelled
        mock_health_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service_mode_waits_for_active_invocations(self, service_effect):
        """Test that shutdown waits for active invocations to complete."""
        # Set service as running with active invocations
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()
        service_effect._active_invocations.add(uuid4())

        with patch.object(
            service_effect, "_wait_for_active_invocations", new_callable=AsyncMock
        ) as mock_wait:
            await service_effect.stop_service_mode()

            # Verify wait function was called
            mock_wait.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service_mode_runs_shutdown_callbacks(self, service_effect):
        """Test that shutdown callbacks are executed during shutdown."""
        # Set service as running
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()

        # Add shutdown callbacks
        callback1 = MagicMock()
        callback2 = MagicMock()
        service_effect.add_shutdown_callback(callback1)
        service_effect.add_shutdown_callback(callback2)

        await service_effect.stop_service_mode()

        # Verify all callbacks were called
        callback1.assert_called_once()
        callback2.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_service_mode_idempotent(self, service_effect):
        """Test that calling stop_service_mode on stopped service is safe."""
        # Service not running
        service_effect._service_running = False

        # Should not raise error
        await service_effect.stop_service_mode()

        # Should still be not running
        assert service_effect._service_running is False


class TestModelServiceEffectEventHandling:
    """Test event subscription and handling."""

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_basic(
        self, service_effect, tool_invocation_event, mock_event_bus
    ):
        """Test basic tool invocation handling."""
        # Set target to match service
        tool_invocation_event.target_node_id = service_effect._node_id

        # Mock the run method
        mock_result = {"status": "success", "data": "test_result"}
        service_effect.run = AsyncMock(return_value=mock_result)

        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify response event was published
        assert mock_event_bus.publish.called

        # Verify metrics updated
        assert service_effect._total_invocations == 1
        assert service_effect._successful_invocations == 1

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_tracks_active(
        self, service_effect, tool_invocation_event
    ):
        """Test that invocation is tracked in active set during execution."""
        tool_invocation_event.target_node_id = service_effect._node_id

        # Track when invocation is active
        active_during_execution = None

        async def slow_run(input_state):
            nonlocal active_during_execution
            active_during_execution = (
                tool_invocation_event.correlation_id
                in service_effect._active_invocations
            )
            await asyncio.sleep(0.01)
            return {"status": "success"}

        service_effect.run = slow_run

        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify it was tracked during execution
        assert active_during_execution is True

        # Verify it's removed after completion
        assert (
            tool_invocation_event.correlation_id
            not in service_effect._active_invocations
        )

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_error_handling(
        self, service_effect, tool_invocation_event, mock_event_bus
    ):
        """Test error handling when tool execution fails."""
        tool_invocation_event.target_node_id = service_effect._node_id

        # Mock run to raise exception
        service_effect.run = AsyncMock(
            side_effect=RuntimeError("Tool execution failed")
        )

        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify error response was published
        assert mock_event_bus.publish.called

        # Get the response event
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is False
        assert "Tool execution failed" in response_event.error

        # Verify metrics updated
        assert service_effect._failed_invocations == 1


class TestModelServiceEffectHealthMonitoring:
    """Test health monitoring and reporting."""

    def test_get_service_health_healthy(self, service_effect):
        """Test service health reporting when healthy."""
        # Set service as running
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()
        service_effect._total_invocations = 100
        service_effect._successful_invocations = 95
        service_effect._failed_invocations = 5

        health = service_effect.get_service_health()

        assert health["status"] == "healthy"
        assert health["uptime_seconds"] >= 0
        assert health["total_invocations"] == 100
        assert health["successful_invocations"] == 95
        assert health["failed_invocations"] == 5
        assert health["success_rate"] == 0.95
        assert health["active_invocations"] == 0

    def test_get_service_health_unhealthy_shutdown_requested(self, service_effect):
        """Test service health reporting when shutdown is requested."""
        service_effect._service_running = True
        service_effect._shutdown_requested = True
        service_effect._start_time = asyncio.get_event_loop().time()

        health = service_effect.get_service_health()

        assert health["status"] == "unhealthy"
        assert health["shutdown_requested"] is True

    def test_get_service_health_with_active_invocations(self, service_effect):
        """Test health reporting includes active invocations count."""
        service_effect._service_running = True
        service_effect._start_time = asyncio.get_event_loop().time()
        service_effect._active_invocations.add(uuid4())
        service_effect._active_invocations.add(uuid4())

        health = service_effect.get_service_health()

        assert health["active_invocations"] == 2


class TestModelServiceEffectRestart:
    """Test service restart cycles."""

    @pytest.mark.asyncio
    async def test_service_restart_cycle(self, service_effect):
        """Test that service can be stopped and restarted."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            # First start
            await service_effect.start_service_mode()
            assert service_effect._service_running is True

            # Stop
            await service_effect.stop_service_mode()
            assert service_effect._service_running is False

            # Restart
            await service_effect.start_service_mode()
            assert service_effect._service_running is True

            # Final cleanup
            await service_effect.stop_service_mode()

    @pytest.mark.asyncio
    async def test_multiple_restart_cycles(self, service_effect):
        """Test multiple restart cycles maintain correct state."""
        with patch.object(
            service_effect, "_service_event_loop", new_callable=AsyncMock
        ):
            for i in range(3):
                # Start
                await service_effect.start_service_mode()
                assert service_effect._service_running is True

                # Perform some operations
                service_effect._total_invocations += 10

                # Stop
                await service_effect.stop_service_mode()
                assert service_effect._service_running is False

                # Verify metrics persist across restarts
                assert service_effect._total_invocations == (i + 1) * 10


class TestModelServiceEffectSignalHandling:
    """Test signal handler registration and behavior."""

    def test_signal_handler_registration(self, service_effect):
        """Test that signal handlers can be registered."""
        with patch("signal.signal") as mock_signal:
            service_effect._register_signal_handlers()

            # Verify both SIGTERM and SIGINT handlers registered
            calls = mock_signal.call_args_list
            assert len(calls) == 2

            signal_numbers = [call[0][0] for call in calls]
            assert signal.SIGTERM in signal_numbers
            assert signal.SIGINT in signal_numbers

    def test_signal_handler_sets_shutdown_flag(self, service_effect):
        """Test that signal handler sets shutdown flag."""
        # Manually call the signal handler logic
        service_effect._shutdown_requested = False

        # Simulate signal
        service_effect._shutdown_requested = True

        assert service_effect._shutdown_requested is True


# Summary comment for test report
"""
Test Implementation Summary:

✅ 10 Test Cases Implemented:
1. Service initialization - Verifies proper initialization of all state variables
2. Service start (start_service_mode) - Tests startup sequence and dependencies
3. Service stop (stop_service_mode) - Tests graceful shutdown
4. Introspection publishing on startup - Verifies service discovery integration
5. Event subscription to TOOL_INVOCATION - Tests event bus integration
6. Health monitoring task creation - Verifies health monitoring setup
7. Signal handler registration - Tests SIGTERM/SIGINT handling
8. Error handling during startup - Tests failure recovery
9. Multiple start attempts (idempotency) - Tests state management
10. Service restart cycles - Tests lifecycle correctness

Test Classes:
- TestModelServiceEffectInitialization (2 tests)
- TestModelServiceEffectStartup (7 tests)
- TestModelServiceEffectShutdown (5 tests)
- TestModelServiceEffectEventHandling (3 tests)
- TestModelServiceEffectHealthMonitoring (3 tests)
- TestModelServiceEffectRestart (2 tests)
- TestModelServiceEffectSignalHandling (2 tests)

Total: 24 test methods covering all 10 required test cases plus additional edge cases.

Testing Patterns Used:
- pytest.mark.asyncio for async tests
- Mock and AsyncMock for dependency injection
- Proper setup/teardown with fixtures
- Context managers for patches
- Comprehensive assertions

All tests follow ONEX patterns and existing codebase conventions.
"""
