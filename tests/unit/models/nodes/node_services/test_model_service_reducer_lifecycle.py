"""
Test suite for ModelServiceReducer lifecycle tests.

Tests service lifecycle, initialization, startup, shutdown, and error scenarios
for the ModelServiceReducer service wrapper with reducer semantics.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.constants.event_types import TOOL_INVOCATION
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.service.model_service_reducer import ModelServiceReducer


class TestModelServiceReducerLifecycle:
    """Test ModelServiceReducer service lifecycle functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ModelONEXContainer for dependency injection."""
        container = Mock(spec=ModelONEXContainer)
        container.event_bus = Mock()
        container.event_bus.publish = AsyncMock()
        container.event_bus.subscribe = Mock()
        return container

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus for publish/subscribe."""
        event_bus = Mock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        return event_bus

    @pytest.fixture
    def service_reducer(self, mock_container):
        """Create ModelServiceReducer instance for testing."""
        service = ModelServiceReducer(mock_container)
        # Inject node_id for testing
        service._node_id = uuid4()
        return service

    @pytest.fixture
    def tool_invocation_event(self):
        """Create ModelToolInvocationEvent for testing."""
        node_id = uuid4()
        return ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="test_reducer",
            tool_name="aggregate_data",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            timeout_ms=10000,
        )

    def test_service_initialization(self, service_reducer):
        """
        Test service initialization.

        Scenario:
        - ModelServiceReducer is instantiated with container
        - All service state attributes are initialized

        Expected:
        - Service state attributes exist with correct defaults
        - Service is not running initially
        - Performance counters are at 0
        - Shutdown callbacks list is empty
        """
        # Verify service state attributes
        assert hasattr(service_reducer, "_service_running")
        assert service_reducer._service_running is False

        assert hasattr(service_reducer, "_service_task")
        assert service_reducer._service_task is None

        assert hasattr(service_reducer, "_health_task")
        assert service_reducer._health_task is None

        assert hasattr(service_reducer, "_active_invocations")
        assert isinstance(service_reducer._active_invocations, set)
        assert len(service_reducer._active_invocations) == 0

        # Verify performance tracking
        assert hasattr(service_reducer, "_total_invocations")
        assert service_reducer._total_invocations == 0

        assert hasattr(service_reducer, "_successful_invocations")
        assert service_reducer._successful_invocations == 0

        assert hasattr(service_reducer, "_failed_invocations")
        assert service_reducer._failed_invocations == 0

        assert hasattr(service_reducer, "_start_time")
        assert service_reducer._start_time is None

        # Verify shutdown handling
        assert hasattr(service_reducer, "_shutdown_requested")
        assert service_reducer._shutdown_requested is False

        assert hasattr(service_reducer, "_shutdown_callbacks")
        assert isinstance(service_reducer._shutdown_callbacks, list)
        assert len(service_reducer._shutdown_callbacks) == 0

    @pytest.mark.asyncio
    async def test_service_start_basic(self, service_reducer, mock_event_bus):
        """
        Test basic service start.

        Scenario:
        - Service is not running
        - start_service_mode() is called
        - Service should start successfully

        Expected:
        - Service running flag set to True
        - Start time recorded
        - Service task created
        """
        service_reducer.event_bus = mock_event_bus

        # Mock internal methods to prevent actual execution
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service in background
            start_task = asyncio.create_task(service_reducer.start_service_mode())

            # Give it time to initialize
            await asyncio.sleep(0.1)

            # Verify service started
            assert service_reducer._service_running is True
            assert service_reducer._start_time is not None

            # Stop the service
            service_reducer._shutdown_requested = True
            await start_task

    @pytest.mark.asyncio
    async def test_service_start_publishes_introspection(
        self, service_reducer, mock_event_bus
    ):
        """
        Test introspection published on startup.

        Scenario:
        - Service starts
        - Introspection should be published for service discovery

        Expected:
        - _publish_introspection_event called
        """
        service_reducer.event_bus = mock_event_bus

        with (
            patch.object(
                service_reducer, "_publish_introspection_event"
            ) as mock_introspection,
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify introspection published
            mock_introspection.assert_called_once()

            # Stop the service
            service_reducer._shutdown_requested = True
            await start_task

    @pytest.mark.asyncio
    async def test_service_start_subscribes_to_tool_invocations(
        self, service_reducer, mock_event_bus
    ):
        """
        Test event subscription to TOOL_INVOCATION.

        Scenario:
        - Service starts
        - Should subscribe to TOOL_INVOCATION events

        Expected:
        - Event bus subscribe called with correct parameters
        """
        service_reducer.event_bus = mock_event_bus

        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify subscription
            mock_event_bus.subscribe.assert_called_once_with(
                service_reducer.handle_tool_invocation, TOOL_INVOCATION
            )

            # Stop the service
            service_reducer._shutdown_requested = True
            await start_task

    @pytest.mark.asyncio
    async def test_service_start_creates_health_monitoring_task(
        self, service_reducer, mock_event_bus
    ):
        """
        Test health monitoring task creation.

        Scenario:
        - Service starts
        - Health monitoring task should be created

        Expected:
        - _health_task exists and is running
        """
        service_reducer.event_bus = mock_event_bus

        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify health task created
            assert service_reducer._health_task is not None
            assert isinstance(service_reducer._health_task, asyncio.Task)
            assert not service_reducer._health_task.done()

            # Stop the service
            service_reducer._shutdown_requested = True
            await start_task

    @pytest.mark.asyncio
    async def test_service_start_registers_signal_handlers(
        self, service_reducer, mock_event_bus
    ):
        """
        Test signal handler registration.

        Scenario:
        - Service starts
        - Signal handlers for SIGTERM and SIGINT should be registered

        Expected:
        - _register_signal_handlers called
        """
        service_reducer.event_bus = mock_event_bus

        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(
                service_reducer, "_register_signal_handlers"
            ) as mock_signal_reg,
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Verify signal handlers registered
            mock_signal_reg.assert_called_once()

            # Stop the service
            service_reducer._shutdown_requested = True
            await start_task

    @pytest.mark.asyncio
    async def test_service_start_without_event_bus(self, service_reducer):
        """
        Test startup without event bus.

        Scenario:
        - Event bus is not available
        - start_service_mode() is called

        Expected:
        - ModelOnexError raised
        - Service not started
        """
        # Remove event bus from all sources
        service_reducer.event_bus = None
        # Also prevent container.get_service() from providing event_bus
        service_reducer.container.get_service = Mock(return_value=None)

        with pytest.raises(ModelOnexError, match="Event bus not available"):
            await service_reducer.start_service_mode()

        # Verify service not started
        assert service_reducer._service_running is False

    @pytest.mark.asyncio
    async def test_service_start_already_running(self, service_reducer, mock_event_bus):
        """
        Test idempotency when already running.

        Scenario:
        - Service is already running
        - start_service_mode() is called again

        Expected:
        - Warning logged
        - No duplicate tasks created
        - Service continues running normally
        """
        service_reducer.event_bus = mock_event_bus
        service_reducer._service_running = True

        with patch.object(service_reducer, "_log_warning") as mock_warning:
            await service_reducer.start_service_mode()

            # Verify warning logged
            mock_warning.assert_called_once()
            assert "already running" in mock_warning.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_service_start_failure_during_startup(
        self, service_reducer, mock_event_bus
    ):
        """
        Test error handling during startup.

        Scenario:
        - Error occurs during service initialization
        - Exception should be handled and propagated

        Expected:
        - Service stopped
        - Exception propagated to caller
        """
        service_reducer.event_bus = mock_event_bus

        # Mock method to raise exception
        with (
            patch.object(
                service_reducer,
                "_publish_introspection_event",
                side_effect=RuntimeError("Introspection failed"),
            ),
            pytest.raises(RuntimeError, match="Introspection failed"),
        ):
            await service_reducer.start_service_mode()

        # Verify service stopped
        assert service_reducer._service_running is False

    @pytest.mark.asyncio
    async def test_service_stop_basic(self, service_reducer, mock_event_bus):
        """
        Test basic service stop.

        Scenario:
        - Service is running
        - stop_service_mode() is called

        Expected:
        - Service stopped gracefully
        - Service running flag set to False
        - Shutdown flag set to True
        """
        service_reducer.event_bus = mock_event_bus

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Stop the service
            await service_reducer.stop_service_mode()

            # Verify service stopped
            assert service_reducer._service_running is False
            assert service_reducer._shutdown_requested is True

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_stop_emits_shutdown_event(
        self, service_reducer, mock_event_bus
    ):
        """
        Test shutdown event emission.

        Scenario:
        - Service is running
        - stop_service_mode() is called

        Expected:
        - Shutdown event emitted via event bus
        """
        service_reducer.event_bus = mock_event_bus

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Stop the service
            await service_reducer.stop_service_mode()

            # Verify shutdown event published
            assert mock_event_bus.publish.call_count >= 1

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_stop_cancels_health_task(
        self, service_reducer, mock_event_bus
    ):
        """
        Test health task cancellation.

        Scenario:
        - Service is running with health task
        - stop_service_mode() is called

        Expected:
        - Health task cancelled properly
        """
        service_reducer.event_bus = mock_event_bus

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Store health task reference
            health_task = service_reducer._health_task

            # Stop the service
            await service_reducer.stop_service_mode()

            # Verify health task cancelled
            assert health_task is not None
            assert health_task.cancelled() or health_task.done()

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_stop_waits_for_active_invocations(
        self, service_reducer, mock_event_bus
    ):
        """
        Test waiting for active invocations.

        Scenario:
        - Service has active invocations
        - stop_service_mode() is called

        Expected:
        - _wait_for_active_invocations called with timeout
        """
        service_reducer.event_bus = mock_event_bus

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Add fake active invocation
            service_reducer._active_invocations.add(uuid4())

            with patch.object(
                service_reducer, "_wait_for_active_invocations", new_callable=AsyncMock
            ) as mock_wait:
                # Stop the service
                await service_reducer.stop_service_mode()

                # Verify wait was called
                mock_wait.assert_called_once()
                assert mock_wait.call_args[1]["timeout_ms"] == 30000

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_stop_runs_shutdown_callbacks(
        self, service_reducer, mock_event_bus
    ):
        """
        Test shutdown callbacks execution.

        Scenario:
        - Service has registered shutdown callbacks
        - stop_service_mode() is called

        Expected:
        - All callbacks executed
        """
        service_reducer.event_bus = mock_event_bus

        # Register shutdown callbacks
        callback1 = Mock()
        callback2 = Mock()
        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback2)

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Stop the service
            await service_reducer.stop_service_mode()

            # Verify callbacks called
            callback1.assert_called_once()
            callback2.assert_called_once()

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_stop_idempotent(self, service_reducer, mock_event_bus):
        """
        Test stopping already stopped service.

        Scenario:
        - Service is not running
        - stop_service_mode() is called

        Expected:
        - No errors
        - Graceful return
        """
        service_reducer.event_bus = mock_event_bus
        service_reducer._service_running = False

        # Should not raise exception
        await service_reducer.stop_service_mode()

        # Verify no errors
        assert service_reducer._service_running is False

    @pytest.mark.asyncio
    async def test_service_stop_with_callback_failure(
        self, service_reducer, mock_event_bus
    ):
        """
        Test callback exception handling.

        Scenario:
        - Shutdown callback raises exception
        - stop_service_mode() is called

        Expected:
        - Error logged
        - Shutdown continues
        - Other callbacks still executed
        """
        service_reducer.event_bus = mock_event_bus

        # Register callbacks with one that fails
        callback1 = Mock()
        callback_failing = Mock(side_effect=RuntimeError("Callback failed"))
        callback2 = Mock()

        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback_failing)
        service_reducer.add_shutdown_callback(callback2)

        # Start service first
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
            patch.object(service_reducer, "_log_error") as mock_error_log,
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Stop the service
            await service_reducer.stop_service_mode()

            # Verify error logged
            mock_error_log.assert_called()

            # Verify all callbacks were called
            callback1.assert_called_once()
            callback_failing.assert_called_once()
            callback2.assert_called_once()

            # Wait for start task to complete
            await start_task

    @pytest.mark.asyncio
    async def test_service_restart_cycle(self, service_reducer, mock_event_bus):
        """
        Test service restart cycles.

        Scenario:
        - Service starts
        - Service stops
        - Service starts again

        Expected:
        - Service can be restarted successfully
        - State is properly reset between cycles
        """
        service_reducer.event_bus = mock_event_bus

        # First cycle: start and stop
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            # Start service
            start_task1 = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)
            assert service_reducer._service_running is True

            # Stop service
            await service_reducer.stop_service_mode()
            await start_task1
            assert service_reducer._service_running is False

            # Reset shutdown flag for restart
            service_reducer._shutdown_requested = False

            # Second cycle: restart
            start_task2 = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)
            assert service_reducer._service_running is True

            # Stop again
            await service_reducer.stop_service_mode()
            await start_task2
            assert service_reducer._service_running is False

    def test_add_shutdown_callback(self, service_reducer):
        """
        Test adding shutdown callbacks.

        Scenario:
        - Callbacks are added via add_shutdown_callback

        Expected:
        - Callbacks stored in list
        """
        callback1 = Mock()
        callback2 = Mock()

        service_reducer.add_shutdown_callback(callback1)
        service_reducer.add_shutdown_callback(callback2)

        assert len(service_reducer._shutdown_callbacks) == 2
        assert callback1 in service_reducer._shutdown_callbacks
        assert callback2 in service_reducer._shutdown_callbacks

    def test_get_service_health_basic(self, service_reducer):
        """
        Test basic health status retrieval.

        Scenario:
        - Service is initialized but not running
        - get_service_health() is called

        Expected:
        - Health dict returned with all required fields
        """
        health = service_reducer.get_service_health()

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

    def test_get_service_health_status_healthy(self, service_reducer):
        """
        Test healthy status reporting.

        Scenario:
        - Service is running
        - Shutdown not requested

        Expected:
        - status == "healthy"
        """
        service_reducer._service_running = True
        service_reducer._shutdown_requested = False

        health = service_reducer.get_service_health()

        assert health["status"] == "healthy"

    def test_get_service_health_status_unhealthy(self, service_reducer):
        """
        Test unhealthy status when shutdown requested.

        Scenario:
        - Shutdown has been requested

        Expected:
        - status == "unhealthy"
        """
        service_reducer._service_running = True
        service_reducer._shutdown_requested = True

        health = service_reducer.get_service_health()

        assert health["status"] == "unhealthy"

    def test_get_service_health_success_rate(self, service_reducer):
        """
        Test success rate calculation.

        Scenario:
        - Service has processed some invocations
        - Some successful, some failed

        Expected:
        - Success rate calculated correctly
        """
        service_reducer._total_invocations = 10
        service_reducer._successful_invocations = 8
        service_reducer._failed_invocations = 2

        health = service_reducer.get_service_health()

        assert health["success_rate"] == 0.8  # 8/10

    def test_get_service_health_success_rate_zero_invocations(self, service_reducer):
        """
        Test success rate with zero invocations.

        Scenario:
        - No invocations processed yet

        Expected:
        - Success rate returns 1.0 (100%)
        """
        service_reducer._total_invocations = 0

        health = service_reducer.get_service_health()

        assert health["success_rate"] == 1.0


class TestModelServiceReducerEdgeCases:
    """Test edge cases and error scenarios for ModelServiceReducer."""

    @pytest.fixture
    def mock_container(self):
        """Create mock container."""
        container = Mock(spec=ModelONEXContainer)
        container.event_bus = Mock()
        container.event_bus.publish = AsyncMock()
        container.event_bus.subscribe = Mock()
        return container

    @pytest.fixture
    def service_reducer(self, mock_container):
        """Create service instance."""
        service = ModelServiceReducer(mock_container)
        service._node_id = uuid4()
        return service

    @pytest.mark.asyncio
    async def test_concurrent_start_attempts(self, service_reducer):
        """
        Test concurrent start attempts.

        Scenario:
        - Multiple start_service_mode() calls are made concurrently

        Expected:
        - Only one service starts
        - Others are ignored with warning
        """
        service_reducer.event_bus = Mock()
        service_reducer.event_bus.publish = AsyncMock()
        service_reducer.event_bus.subscribe = Mock()

        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
            patch.object(service_reducer, "_log_warning") as mock_warning,
        ):
            # Start multiple times concurrently
            tasks = [
                asyncio.create_task(service_reducer.start_service_mode())
                for _ in range(3)
            ]

            await asyncio.sleep(0.1)

            # One should start, others should warn
            assert service_reducer._service_running is True

            # Stop service
            service_reducer._shutdown_requested = True

            # Wait for all tasks
            await asyncio.gather(*tasks, return_exceptions=True)

    @pytest.mark.asyncio
    async def test_cleanup_event_handlers_called(self, service_reducer):
        """
        Test cleanup_event_handlers is called during shutdown.

        Scenario:
        - Service is running
        - stop_service_mode() is called

        Expected:
        - cleanup_event_handlers called
        """
        service_reducer.event_bus = Mock()
        service_reducer.event_bus.publish = AsyncMock()
        service_reducer.event_bus.subscribe = Mock()

        # Mock cleanup method
        service_reducer.cleanup_event_handlers = Mock()

        # Start service
        with (
            patch.object(service_reducer, "_publish_introspection_event"),
            patch.object(service_reducer, "_register_signal_handlers"),
            patch.object(
                service_reducer, "_service_event_loop", new_callable=AsyncMock
            ),
        ):
            start_task = asyncio.create_task(service_reducer.start_service_mode())
            await asyncio.sleep(0.1)

            # Stop service
            await service_reducer.stop_service_mode()

            # Verify cleanup called
            service_reducer.cleanup_event_handlers.assert_called_once()

            await start_task
