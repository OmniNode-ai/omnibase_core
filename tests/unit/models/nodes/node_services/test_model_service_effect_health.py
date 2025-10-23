"""
Health Monitoring and Graceful Shutdown Tests for ModelServiceEffect.

Test suite covering health monitoring and graceful shutdown capabilities:
- Health status retrieval and metrics calculation
- Health monitoring loop and periodic logging
- Graceful shutdown with active invocation handling
- Shutdown callbacks and signal handlers
- Resource cleanup and error handling

Test Plan Reference:
    Section 5.3: Health Monitoring Tests
    Section 5.4: Graceful Shutdown Tests
"""

import asyncio
import signal
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, call, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.contracts.model_contract_effect import ModelContractEffect
from omnibase_core.models.discovery.model_node_shutdown_event import (
    ModelNodeShutdownEvent,
)
from omnibase_core.models.nodes.node_services.model_service_effect import (
    ModelServiceEffect,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_container() -> MagicMock:
    """Create mock ONEX container."""
    container = MagicMock(spec=ModelONEXContainer)
    return container


@pytest.fixture
def mock_event_bus() -> AsyncMock:
    """Create mock event bus."""
    event_bus = AsyncMock()
    event_bus.subscribe = Mock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def service_effect(mock_container: MagicMock, mock_event_bus: AsyncMock) -> MagicMock:
    """Create mock ModelServiceEffect instance for testing."""
    # Create a mock that mimics ModelServiceEffect behavior
    service = MagicMock(spec=ModelServiceEffect)
    service._node_id = uuid4()
    service.event_bus = mock_event_bus
    service._get_event_bus = Mock(
        return_value=mock_event_bus
    )  # Mock event bus resolution
    service._extract_node_name = Mock(return_value="TestServiceEffect")
    service._publish_introspection_event = Mock()
    service.cleanup_event_handlers = Mock()

    # Initialize service state attributes
    service._service_running = False
    service._service_task = None
    service._health_task = None
    service._active_invocations = set()
    service._shutdown_requested = False
    service._shutdown_callbacks = []

    # Initialize performance tracking
    service._total_invocations = 0
    service._successful_invocations = 0
    service._failed_invocations = 0
    service._start_time = None

    # Bind real methods from MixinNodeService
    from omnibase_core.mixins.mixin_node_service import MixinNodeService

    # Import bound methods that we need to test
    service.get_service_health = lambda: MixinNodeService.get_service_health(service)
    service.add_shutdown_callback = (
        lambda callback: MixinNodeService.add_shutdown_callback(service, callback)
    )
    service._wait_for_active_invocations = (
        lambda timeout_ms=30000: MixinNodeService._wait_for_active_invocations(
            service, timeout_ms
        )
    )
    service._emit_shutdown_event = lambda: MixinNodeService._emit_shutdown_event(
        service
    )
    service._health_monitor_loop = lambda: MixinNodeService._health_monitor_loop(
        service
    )
    service._register_signal_handlers = (
        lambda: MixinNodeService._register_signal_handlers(service)
    )
    service._log_info = Mock()
    service._log_warning = Mock()
    service._log_error = Mock()

    async def async_stop_service_mode():
        return await MixinNodeService.stop_service_mode(service)

    service.stop_service_mode = async_stop_service_mode

    return service


@pytest.fixture
def correlation_id() -> UUID:
    """Generate correlation ID."""
    return uuid4()


# ============================================================================
# Health Status Retrieval Tests
# ============================================================================


class TestServiceHealthRetrieval:
    """Test health status retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_service_health_basic(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test basic health status retrieval.

        Scenario:
        - Service initialized but not started
        - Health status requested
        - All required fields present

        Expected:
        - Dict returned with all required health fields
        - Status is "unhealthy" (not started)
        - Counters initialized to zero
        """
        health = service_effect.get_service_health()

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

    @pytest.mark.asyncio
    async def test_get_service_health_status_healthy(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test healthy status when service is running.

        Scenario:
        - Service is running
        - No shutdown requested
        - Health status requested

        Expected:
        - Status is "healthy"
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = False

        health = service_effect.get_service_health()

        assert health["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_get_service_health_status_unhealthy(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test unhealthy status when shutdown requested.

        Scenario:
        - Service is running
        - Shutdown requested
        - Health status requested

        Expected:
        - Status is "unhealthy"
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = True

        health = service_effect.get_service_health()

        assert health["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_get_service_health_uptime_calculation(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test uptime calculation with mocked time.

        Scenario:
        - Service started at specific time
        - Current time is known
        - Health status requested

        Expected:
        - Uptime calculated correctly
        """
        start_time = 1000.0
        current_time = 1045.5  # 45.5 seconds later

        with patch("time.time", return_value=current_time):
            service_effect._start_time = start_time
            health = service_effect.get_service_health()

        assert health["uptime_seconds"] == 45  # int(45.5) = 45

    @pytest.mark.asyncio
    async def test_get_service_health_active_invocations(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test active invocations count in health status.

        Scenario:
        - Service has active invocations tracked
        - Health status requested

        Expected:
        - Count matches _active_invocations set size
        """
        # Add some correlation IDs to active invocations
        service_effect._active_invocations = {uuid4(), uuid4(), uuid4()}

        health = service_effect.get_service_health()

        assert health["active_invocations"] == 3

    @pytest.mark.asyncio
    async def test_get_service_health_success_rate(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test success rate calculation.

        Scenario:
        - Service has completed invocations
        - Mix of successful and failed invocations
        - Health status requested

        Expected:
        - Success rate calculated as (successful / total)
        """
        service_effect._total_invocations = 100
        service_effect._successful_invocations = 85
        service_effect._failed_invocations = 15

        health = service_effect.get_service_health()

        assert health["success_rate"] == 0.85  # 85/100

    @pytest.mark.asyncio
    async def test_get_service_health_success_rate_zero_invocations(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test success rate with zero invocations.

        Scenario:
        - Service has no invocations yet
        - Health status requested

        Expected:
        - Success rate is 1.0 (100%)
        """
        service_effect._total_invocations = 0
        service_effect._successful_invocations = 0
        service_effect._failed_invocations = 0

        health = service_effect.get_service_health()

        assert health["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_get_service_health_before_start(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test health status before service started.

        Scenario:
        - Service not yet started (_start_time is None)
        - Health status requested

        Expected:
        - uptime_seconds is 0
        """
        service_effect._start_time = None

        health = service_effect.get_service_health()

        assert health["uptime_seconds"] == 0


# ============================================================================
# Health Monitoring Loop Tests
# ============================================================================


class TestHealthMonitoringLoop:
    """Test health monitoring loop functionality."""

    @pytest.mark.asyncio
    async def test_health_monitor_loop_runs_while_active(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test health monitoring loop runs during service lifetime.

        Scenario:
        - Service is running
        - Health monitoring loop started
        - Loop checks health periodically

        Expected:
        - get_service_health called during monitoring
        - Loop continues while service running
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = False

        # Mock get_service_health to track calls
        original_get_health = service_effect.get_service_health
        call_count = 0

        def mock_get_health():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                # Stop after 2 calls to prevent infinite loop
                service_effect._shutdown_requested = True
            return original_get_health()

        service_effect.get_service_health = mock_get_health

        # Run health monitor loop with mocked sleep
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service_effect._health_monitor_loop()

        assert call_count >= 2
        assert mock_sleep.called

    @pytest.mark.asyncio
    async def test_health_monitor_loop_logs_periodically(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test periodic health logging every 100 invocations.

        Scenario:
        - Service running with invocation count at 100
        - Health monitoring loop checks health
        - Log should be emitted

        Expected:
        - Health info logged when total_invocations % 100 == 0
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = False
        service_effect._total_invocations = 100

        # Mock _log_info to track calls
        with patch.object(service_effect, "_log_info") as mock_log_info:
            # Stop immediately after first health check
            original_get_health = service_effect.get_service_health

            def mock_get_health():
                service_effect._shutdown_requested = True
                return original_get_health()

            service_effect.get_service_health = mock_get_health

            with patch("asyncio.sleep", new_callable=AsyncMock):
                await service_effect._health_monitor_loop()

        # Check that health was logged
        logged_health = any(
            "Health:" in str(call_args) for call_args in mock_log_info.call_args_list
        )
        assert logged_health

    @pytest.mark.asyncio
    async def test_health_monitor_loop_sleep_interval(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test sleep interval between health checks.

        Scenario:
        - Health monitoring loop running
        - Sleep called between iterations

        Expected:
        - Sleep called with 30 second interval
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = False

        # Stop after first iteration
        iteration_count = 0

        async def mock_sleep(seconds: float) -> None:
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count >= 1:
                service_effect._shutdown_requested = True

        with patch("asyncio.sleep", side_effect=mock_sleep) as mock_sleep_call:
            await service_effect._health_monitor_loop()

        # Check that sleep was called with 30 seconds
        mock_sleep_call.assert_called_with(30)

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_cancellation(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test health monitor loop handles CancelledError gracefully.

        Scenario:
        - Health monitoring loop running
        - Task cancelled (CancelledError raised)

        Expected:
        - CancelledError caught and logged
        - No exception propagated
        """
        service_effect._service_running = True

        # Mock sleep to raise CancelledError
        with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
            with patch.object(service_effect, "_log_info") as mock_log_info:
                await service_effect._health_monitor_loop()

        # Check that cancellation was logged
        cancellation_logged = any(
            "cancelled" in str(call_args).lower()
            for call_args in mock_log_info.call_args_list
        )
        assert cancellation_logged

    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_exceptions(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test health monitor loop handles exceptions gracefully.

        Scenario:
        - Health monitoring loop running
        - Exception raised during health check
        - get_service_health raises RuntimeError

        Expected:
        - Exception caught and logged
        - No exception propagated
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = False

        # Mock get_service_health to raise exception
        def mock_get_health():
            service_effect._shutdown_requested = True
            raise RuntimeError("Health check failed")

        service_effect.get_service_health = mock_get_health

        with patch.object(service_effect, "_log_error") as mock_log_error:
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await service_effect._health_monitor_loop()

        # Check that error was logged
        assert mock_log_error.called
        error_logged = any(
            "Health monitor error" in str(call_args)
            for call_args in mock_log_error.call_args_list
        )
        assert error_logged

    @pytest.mark.asyncio
    async def test_health_monitor_loop_stops_on_shutdown(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test health monitor loop exits on shutdown.

        Scenario:
        - Health monitoring loop running
        - Shutdown requested

        Expected:
        - Loop terminates gracefully
        """
        service_effect._service_running = True
        service_effect._shutdown_requested = True

        # Health monitor should exit immediately
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await service_effect._health_monitor_loop()

        # Should not sleep if shutdown already requested
        assert not mock_sleep.called


# ============================================================================
# Graceful Shutdown Tests
# ============================================================================


class TestGracefulShutdown:
    """Test graceful shutdown functionality."""

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_none(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test wait with no active invocations.

        Scenario:
        - No active invocations
        - Wait for invocations called

        Expected:
        - Returns immediately
        """
        service_effect._active_invocations = set()

        start_time = time.time()
        await service_effect._wait_for_active_invocations(timeout_ms=5000)
        elapsed = time.time() - start_time

        # Should return almost immediately
        assert elapsed < 0.1

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_completes_in_time(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test wait for invocations that complete within timeout.

        Scenario:
        - Active invocations present
        - Invocations complete before timeout

        Expected:
        - Returns when all invocations complete
        """
        correlation_id = uuid4()
        service_effect._active_invocations = {correlation_id}

        # Simulate invocation completing after short delay
        async def remove_invocation():
            await asyncio.sleep(0.2)
            service_effect._active_invocations.discard(correlation_id)

        # Start task to remove invocation (store reference to prevent garbage collection)
        task = asyncio.create_task(remove_invocation())
        assert task is not None  # Keep reference alive

        start_time = time.time()
        await service_effect._wait_for_active_invocations(timeout_ms=5000)
        elapsed = time.time() - start_time

        # Should complete after ~0.2 seconds
        assert 0.15 < elapsed < 0.5
        assert len(service_effect._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_timeout(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test timeout with active invocations still pending.

        Scenario:
        - Active invocations present
        - Invocations do not complete before timeout

        Expected:
        - Warning logged
        - Returns after timeout
        """
        correlation_id = uuid4()
        service_effect._active_invocations = {correlation_id}

        with patch.object(service_effect, "_log_warning") as mock_log_warning:
            await service_effect._wait_for_active_invocations(timeout_ms=100)

        # Warning should be logged about timeout
        assert mock_log_warning.called
        warning_logged = any(
            "Timeout waiting" in str(call_args)
            for call_args in mock_log_warning.call_args_list
        )
        assert warning_logged

        # Invocation should still be active
        assert correlation_id in service_effect._active_invocations

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_partial_completion(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test partial completion before timeout.

        Scenario:
        - Multiple active invocations
        - Some complete, some don't
        - Timeout reached

        Expected:
        - Warning logged with remaining count
        - Returns after timeout
        """
        correlation_id_1 = uuid4()
        correlation_id_2 = uuid4()
        service_effect._active_invocations = {correlation_id_1, correlation_id_2}

        # Simulate one invocation completing
        async def remove_one_invocation():
            await asyncio.sleep(0.05)
            service_effect._active_invocations.discard(correlation_id_1)

        # Store reference to prevent garbage collection
        task = asyncio.create_task(remove_one_invocation())
        assert task is not None  # Keep reference alive

        with patch.object(service_effect, "_log_warning") as mock_log_warning:
            await service_effect._wait_for_active_invocations(timeout_ms=100)

        # Should log warning about 1 remaining invocation
        assert mock_log_warning.called
        assert len(service_effect._active_invocations) == 1

    @pytest.mark.asyncio
    async def test_wait_for_active_invocations_custom_timeout(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test custom timeout value respected.

        Scenario:
        - Active invocations present
        - Custom short timeout specified
        - Invocations don't complete

        Expected:
        - Returns after custom timeout
        """
        correlation_id = uuid4()
        service_effect._active_invocations = {correlation_id}

        start_time = time.time()
        await service_effect._wait_for_active_invocations(timeout_ms=200)
        elapsed = time.time() - start_time

        # Should timeout after ~0.2 seconds
        assert 0.15 < elapsed < 0.4


# ============================================================================
# Shutdown Event Emission Tests
# ============================================================================


class TestShutdownEventEmission:
    """Test shutdown event emission functionality."""

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_success(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test successful shutdown event emission.

        Scenario:
        - Event bus available
        - Shutdown event emitted

        Expected:
        - Event published with correct data
        - Event type is NODE_SHUTDOWN
        """
        await service_effect._emit_shutdown_event()

        # Check that publish was called
        assert mock_event_bus.publish.called

        # Extract the published event
        published_event = mock_event_bus.publish.call_args[0][0]

        assert isinstance(published_event, ModelNodeShutdownEvent)
        assert published_event.node_id == service_effect._node_id

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_without_event_bus(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test shutdown event emission without event bus.

        Scenario:
        - Event bus not available
        - Shutdown event emission attempted

        Expected:
        - No crash
        - No exception raised
        """
        service_effect.event_bus = None

        # Should not raise exception
        await service_effect._emit_shutdown_event()

    @pytest.mark.asyncio
    async def test_emit_shutdown_event_failure(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test shutdown event emission failure handling.

        Scenario:
        - Event bus publish fails
        - Exception raised during publish

        Expected:
        - Error logged
        - Exception caught (not propagated)
        """
        mock_event_bus.publish.side_effect = RuntimeError("Event bus publish failed")

        with patch.object(service_effect, "_log_error") as mock_log_error:
            # Should not raise exception
            await service_effect._emit_shutdown_event()

        # Error should be logged
        assert mock_log_error.called


# ============================================================================
# Shutdown Callbacks Tests
# ============================================================================


class TestShutdownCallbacks:
    """Test shutdown callback functionality."""

    @pytest.mark.asyncio
    async def test_add_shutdown_callback(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test adding shutdown callback.

        Scenario:
        - Callback function added
        - Callback stored in list

        Expected:
        - Callback stored
        """
        callback = Mock()
        service_effect.add_shutdown_callback(callback)

        assert callback in service_effect._shutdown_callbacks

    @pytest.mark.asyncio
    async def test_add_multiple_shutdown_callbacks(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test adding multiple callbacks.

        Scenario:
        - Multiple callbacks added
        - All callbacks stored

        Expected:
        - All callbacks in list
        """
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        service_effect.add_shutdown_callback(callback1)
        service_effect.add_shutdown_callback(callback2)
        service_effect.add_shutdown_callback(callback3)

        assert len(service_effect._shutdown_callbacks) == 3
        assert callback1 in service_effect._shutdown_callbacks
        assert callback2 in service_effect._shutdown_callbacks
        assert callback3 in service_effect._shutdown_callbacks

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_executed(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test callbacks executed on shutdown.

        Scenario:
        - Callbacks registered
        - Service stopped
        - Callbacks executed

        Expected:
        - All callbacks called
        """
        callback1 = Mock()
        callback2 = Mock()

        service_effect.add_shutdown_callback(callback1)
        service_effect.add_shutdown_callback(callback2)

        service_effect._service_running = True
        service_effect._active_invocations = set()
        service_effect.cleanup_event_handlers = Mock()

        await service_effect.stop_service_mode()

        assert callback1.called
        assert callback2.called

    @pytest.mark.asyncio
    async def test_shutdown_callbacks_execution_order(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test callbacks executed in registration order.

        Scenario:
        - Callbacks registered in specific order
        - Service stopped
        - Callbacks executed in order

        Expected:
        - Callbacks called in registration order
        """
        call_order = []

        def callback1():
            call_order.append(1)

        def callback2():
            call_order.append(2)

        def callback3():
            call_order.append(3)

        service_effect.add_shutdown_callback(callback1)
        service_effect.add_shutdown_callback(callback2)
        service_effect.add_shutdown_callback(callback3)

        service_effect._service_running = True
        service_effect._active_invocations = set()
        service_effect.cleanup_event_handlers = Mock()

        await service_effect.stop_service_mode()

        assert call_order == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_shutdown_callback_exception_handling(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test exception in callback doesn't stop other callbacks.

        Scenario:
        - Multiple callbacks registered
        - One callback raises exception
        - Other callbacks should still run

        Expected:
        - Error logged
        - Other callbacks executed
        """
        callback1 = Mock()
        callback2 = Mock(side_effect=RuntimeError("Callback failed"))
        callback3 = Mock()

        service_effect.add_shutdown_callback(callback1)
        service_effect.add_shutdown_callback(callback2)
        service_effect.add_shutdown_callback(callback3)

        service_effect._service_running = True
        service_effect._active_invocations = set()
        service_effect.cleanup_event_handlers = Mock()

        with patch.object(service_effect, "_log_error") as mock_log_error:
            await service_effect.stop_service_mode()

        # All callbacks should be called
        assert callback1.called
        assert callback2.called
        assert callback3.called

        # Error should be logged
        assert mock_log_error.called


# ============================================================================
# Signal Handler Tests
# ============================================================================


class TestSignalHandlers:
    """Test signal handler functionality."""

    @pytest.mark.asyncio
    async def test_register_signal_handlers_success(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test successful signal handler registration.

        Scenario:
        - Signal handlers registered
        - SIGTERM and SIGINT handlers set

        Expected:
        - signal.signal called for SIGTERM and SIGINT
        """
        with patch("signal.signal") as mock_signal:
            service_effect._register_signal_handlers()

        # Should register both SIGTERM and SIGINT
        assert mock_signal.call_count == 2
        signal_calls = [call_args[0][0] for call_args in mock_signal.call_args_list]
        assert signal.SIGTERM in signal_calls
        assert signal.SIGINT in signal_calls

    @pytest.mark.asyncio
    async def test_register_signal_handlers_failure(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test signal handler registration failure.

        Scenario:
        - signal.signal raises exception
        - Registration fails

        Expected:
        - Warning logged
        - No exception propagated
        """
        with patch("signal.signal", side_effect=RuntimeError("Cannot register signal")):
            with patch.object(service_effect, "_log_warning") as mock_log_warning:
                service_effect._register_signal_handlers()

        assert mock_log_warning.called

    @pytest.mark.asyncio
    async def test_signal_handler_sets_shutdown_flag(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test signal handler sets shutdown flag.

        Scenario:
        - Signal handler registered
        - Signal received
        - Handler invoked

        Expected:
        - _shutdown_requested set to True
        """
        captured_handler = None

        def capture_handler(signum, handler):
            nonlocal captured_handler
            captured_handler = handler

        with patch("signal.signal", side_effect=capture_handler):
            service_effect._register_signal_handlers()

        # Invoke the captured handler
        assert captured_handler is not None
        service_effect._shutdown_requested = False
        captured_handler(signal.SIGTERM, None)

        assert service_effect._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_signal_handler_logs_signal(
        self, service_effect: ModelServiceEffect
    ) -> None:
        """
        Test signal handler logs the received signal.

        Scenario:
        - Signal handler registered
        - Signal received
        - Handler invoked

        Expected:
        - Log message with signal number
        """
        captured_handler = None

        def capture_handler(signum, handler):
            nonlocal captured_handler
            captured_handler = handler

        with patch("signal.signal", side_effect=capture_handler):
            service_effect._register_signal_handlers()

        with patch.object(service_effect, "_log_info") as mock_log_info:
            captured_handler(signal.SIGTERM, None)

        # Check that signal was logged
        assert mock_log_info.called
        log_message = str(mock_log_info.call_args)
        assert "signal" in log_message.lower()


# ============================================================================
# Shutdown Integration Tests
# ============================================================================


class TestShutdownIntegration:
    """Test integrated shutdown scenarios."""

    @pytest.mark.asyncio
    async def test_shutdown_during_active_invocation(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test shutdown with active invocation in progress.

        Scenario:
        - Service running with active invocation
        - Shutdown initiated
        - Waits for invocation

        Expected:
        - Wait called
        - Service stops gracefully
        """
        correlation_id = uuid4()
        service_effect._service_running = True
        service_effect._active_invocations = {correlation_id}
        service_effect.cleanup_event_handlers = Mock()

        # Simulate invocation completing during wait
        async def remove_invocation():
            await asyncio.sleep(0.1)
            service_effect._active_invocations.discard(correlation_id)

        # Store reference to prevent garbage collection
        task = asyncio.create_task(remove_invocation())
        assert task is not None  # Keep reference alive

        await service_effect.stop_service_mode()

        assert service_effect._service_running is False
        assert len(service_effect._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_health_task_cancellation(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test health task cancellation during shutdown.

        Scenario:
        - Health monitoring task running
        - Shutdown initiated
        - Health task cancelled

        Expected:
        - Health task cancelled
        - No errors
        """
        # Create mock health task
        health_task = Mock()
        health_task.done = Mock(return_value=False)
        health_task.cancel = Mock()

        service_effect._service_running = True
        service_effect._health_task = health_task
        service_effect._active_invocations = set()
        service_effect.cleanup_event_handlers = Mock()

        await service_effect.stop_service_mode()

        # Health task should be cancelled
        assert health_task.cancel.called

    @pytest.mark.asyncio
    async def test_resource_cleanup(
        self, service_effect: ModelServiceEffect, mock_event_bus: AsyncMock
    ) -> None:
        """
        Test complete resource cleanup during shutdown.

        Scenario:
        - Service running with resources
        - Shutdown initiated
        - All resources cleaned up

        Expected:
        - Event handlers cleaned up
        - Service flag cleared
        - Shutdown event emitted
        """
        service_effect._service_running = True
        service_effect._active_invocations = set()
        service_effect.cleanup_event_handlers = Mock()

        await service_effect.stop_service_mode()

        # Check cleanup was called
        assert service_effect.cleanup_event_handlers.called

        # Service should be stopped
        assert service_effect._service_running is False

        # Shutdown event should be emitted
        assert mock_event_bus.publish.called
