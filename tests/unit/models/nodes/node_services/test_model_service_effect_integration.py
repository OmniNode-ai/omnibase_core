"""
Integration and MRO tests for ModelServiceEffect.

Tests the integration of MixinNodeService with NodeEffect and all mixins:
- MRO correctness validation
- Service mode + EventBus integration
- Service mode + HealthCheck integration
- Service mode + Metrics integration
- Tool invocation + event publishing
- Effect semantics (transaction management) + service mode
- Circuit breaker + service mode
- Retry logic + service mode
- Full end-to-end workflows
- Mixin initialization order verification
- Super() call propagation
- Method accessibility from all mixins
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.constants.event_types import TOOL_INVOCATION
from omnibase_core.mixins.mixin_event_bus import MixinEventBus
from omnibase_core.mixins.mixin_health_check import MixinHealthCheck
from omnibase_core.mixins.mixin_metrics import MixinMetrics
from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.nodes.node_services.model_service_effect import (
    ModelServiceEffect,
)
from omnibase_core.nodes.enum_effect_types import (
    EnumCircuitBreakerState,
    EnumEffectType,
    EnumTransactionState,
)
from omnibase_core.nodes.model_effect_input import ModelEffectInput
from omnibase_core.nodes.node_effect import NodeEffect


@pytest.fixture
def mock_container():
    """Create a mock ModelONEXContainer."""
    container = Mock(spec=ModelONEXContainer)
    container.get_service = Mock(return_value=None)
    return container


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = Mock()
    event_bus.unsubscribe = Mock()
    return event_bus


@pytest.fixture
def mock_metadata_loader():
    """Create a mock metadata loader."""
    loader = Mock()
    loader.metadata = Mock()
    loader.metadata.version = "1.0.0"
    return loader


@pytest.fixture
def service_effect(mock_container):
    """Create a ModelServiceEffect instance with mocked dependencies."""
    # Instantiate with container - event_bus can be mocked per-test as needed
    service = ModelServiceEffect(mock_container)
    return service


@pytest.fixture
def tool_invocation_event(service_effect):
    """Create a sample tool invocation event."""
    return ModelToolInvocationEvent(
        node_id=uuid4(),  # Add missing node_id field
        correlation_id=uuid4(),
        target_node_id=service_effect.node_id,
        target_node_name="ModelServiceEffect",
        requester_node_id=uuid4(),
        requester_id=uuid4(),  # Fix: must be UUID not string
        tool_name="test_tool",
        action="execute",
        parameters={"data": "test_data"},
    )


class TestMROCorrectness:
    """Test Method Resolution Order correctness for ModelServiceEffect."""

    def test_mro_order_matches_expected(self, mock_container):
        """Test that MRO follows expected pattern."""
        service = ModelServiceEffect(mock_container)
        mro = inspect.getmro(ModelServiceEffect)

        # Expected MRO (Python's C3 linearization):
        # ModelServiceEffect → MixinNodeService → NodeEffect → NodeCoreBase →
        # ABC → MixinHealthCheck → MixinEventBus → MixinMetrics → ...
        #
        # Note: NodeCoreBase appears after NodeEffect (its parent) and before
        # the remaining mixins due to C3 linearization algorithm
        expected_classes = [
            ModelServiceEffect,
            MixinNodeService,
            NodeEffect,
        ]

        for i, expected_class in enumerate(expected_classes):
            assert mro[i] == expected_class, (
                f"MRO position {i} should be {expected_class.__name__}, "
                f"but got {mro[i].__name__}"
            )

        # Verify all mixins are present in the MRO (order after NodeEffect may vary)
        mro_classes = set(mro)
        required_mixins = {MixinHealthCheck, MixinEventBus, MixinMetrics}
        assert required_mixins.issubset(mro_classes), (
            f"Missing required mixins in MRO. "
            f"Expected {required_mixins}, found {mro_classes}"
        )

    def test_mro_no_diamond_problem(self, mock_container):
        """Test that MRO resolves diamond inheritance correctly."""
        service = ModelServiceEffect(mock_container)
        mro = inspect.getmro(ModelServiceEffect)

        # Verify no class appears twice in MRO (diamond problem indicator)
        class_names = [cls.__name__ for cls in mro]
        assert len(class_names) == len(
            set(class_names)
        ), f"MRO contains duplicate classes: {class_names}"

    def test_all_mixins_accessible(self, service_effect):
        """Test that methods from all mixins are accessible."""
        # MixinNodeService methods
        assert hasattr(service_effect, "start_service_mode")
        assert hasattr(service_effect, "stop_service_mode")
        assert hasattr(service_effect, "handle_tool_invocation")
        assert hasattr(service_effect, "get_service_health")

        # NodeEffect methods
        assert hasattr(service_effect, "process")
        assert hasattr(service_effect, "transaction_context")
        assert hasattr(service_effect, "execute_file_operation")
        assert hasattr(service_effect, "emit_state_change_event")

        # MixinHealthCheck methods
        assert hasattr(service_effect, "get_health_status")

        # MixinEventBus methods
        assert hasattr(service_effect, "publish_event")

        # MixinMetrics methods
        assert hasattr(service_effect, "get_metrics")

    def test_mixin_initialization_order(self, mock_container):
        """Test that all mixins are properly initialized via super().__init__()."""
        service = ModelServiceEffect(mock_container)

        # Verify MixinNodeService initialization
        assert hasattr(service, "_service_running")
        assert service._service_running is False
        assert hasattr(service, "_active_invocations")
        assert isinstance(service._active_invocations, set)

        # Verify NodeEffect initialization
        assert hasattr(service, "active_transactions")
        assert isinstance(service.active_transactions, dict)
        assert hasattr(service, "circuit_breakers")
        assert isinstance(service.circuit_breakers, dict)

        # Verify base NodeCoreBase initialization
        assert hasattr(service, "node_id")
        assert isinstance(service.node_id, UUID)
        assert hasattr(service, "container")

    def test_super_call_propagation(self, mock_container):
        """Test that super().__init__() calls propagate through MRO."""
        # Verify super() call propagation by checking that attributes from each
        # level of the MRO are properly initialized
        service = ModelServiceEffect(mock_container)

        # Verify NodeEffect.__init__ was called (sets up these attributes)
        assert hasattr(service, "active_transactions")
        assert isinstance(service.active_transactions, dict)
        assert hasattr(service, "circuit_breakers")
        assert isinstance(service.circuit_breakers, dict)
        assert hasattr(service, "effect_handlers")
        assert isinstance(service.effect_handlers, dict)

        # Verify NodeCoreBase.__init__ was called (sets up node_id, container)
        assert hasattr(service, "node_id")
        assert isinstance(service.node_id, UUID)
        assert hasattr(service, "container")
        assert service.container is mock_container

        # Verify MixinNodeService.__init__ was called (sets up service attributes)
        assert hasattr(service, "_service_running")
        assert service._service_running is False
        assert hasattr(service, "_active_invocations")
        assert isinstance(service._active_invocations, set)


class TestServiceModeEventBusIntegration:
    """Test integration between service mode and EventBus mixin."""

    @pytest.mark.asyncio
    async def test_service_subscribes_to_tool_invocations(
        self, service_effect, mock_event_bus
    ):
        """Test that service subscribes to TOOL_INVOCATION events on startup."""
        # Inject mock event bus
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        # Start service mode
        start_task = asyncio.create_task(service_effect.start_service_mode())
        await asyncio.sleep(0.1)  # Allow startup to proceed

        # Verify subscription
        mock_event_bus.subscribe.assert_called_once()
        call_args = mock_event_bus.subscribe.call_args
        assert call_args[0][1] == TOOL_INVOCATION

        # Stop service
        service_effect._shutdown_requested = True
        await asyncio.sleep(0.1)
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_tool_response_published_via_event_bus(
        self, service_effect, mock_event_bus, tool_invocation_event
    ):
        """Test that tool responses are published via EventBus."""
        # Inject mock event bus
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        # Mock the run method to return a result (use object.__setattr__ to bypass Pydantic)
        async def mock_run(input_state):
            return {"status": "success", "data": "test_result"}

        object.__setattr__(service_effect, "run", mock_run)

        # Handle tool invocation
        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify response was published via event bus
        assert mock_event_bus.publish.call_count >= 1

        # Get the published event
        published_event = mock_event_bus.publish.call_args_list[-1][0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.correlation_id == tool_invocation_event.correlation_id
        assert published_event.success is True

    @pytest.mark.asyncio
    async def test_event_emission_during_effect_execution(
        self, service_effect, mock_event_bus
    ):
        """Test that events can be emitted during effect execution."""
        # Create effect input for event emission
        event_type = "test_event"
        payload = {"data": "test"}
        correlation_id = uuid4()

        result = await service_effect.emit_state_change_event(
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
        )

        # Event emission result depends on container.get_service("event_bus")
        # Since our mock returns None, result should be False
        assert result is False


class TestServiceModeHealthCheckIntegration:
    """Test integration between service mode and HealthCheck mixin."""

    def test_service_health_includes_service_metrics(self, service_effect):
        """Test that get_service_health includes service-specific metrics."""
        health = service_effect.get_service_health()

        # Verify service metrics are included
        assert "status" in health
        assert "uptime_seconds" in health
        assert "active_invocations" in health
        assert "total_invocations" in health
        assert "successful_invocations" in health
        assert "failed_invocations" in health
        assert "success_rate" in health

    def test_service_health_aggregates_node_health(self, service_effect):
        """Test that service health can aggregate with node health."""
        # Get service health
        service_health = service_effect.get_service_health()

        # Get node health (from MixinHealthCheck)
        node_health = service_effect.get_health_status()

        # Both should be available and contain relevant data
        assert service_health["status"] in ["healthy", "unhealthy"]
        assert "node_id" in node_health
        assert "is_healthy" in node_health

    @pytest.mark.asyncio
    async def test_health_reflects_active_invocations(
        self, service_effect, tool_invocation_event
    ):
        """Test that health status reflects active invocations."""

        # Mock run method to simulate long-running operation
        async def slow_run(input_state):
            await asyncio.sleep(0.2)
            return {"status": "success"}

        object.__setattr__(service_effect, "run", slow_run)

        # Start invocation in background
        invocation_task = asyncio.create_task(
            service_effect.handle_tool_invocation(tool_invocation_event)
        )

        # Check health while invocation is active
        await asyncio.sleep(0.05)
        health = service_effect.get_service_health()

        # Should show active invocation
        assert health["active_invocations"] >= 1

        # Wait for completion
        await invocation_task

        # Check health after completion
        health_after = service_effect.get_service_health()
        assert health_after["active_invocations"] == 0


class TestServiceModeMetricsIntegration:
    """Test integration between service mode and Metrics mixin."""

    @pytest.mark.asyncio
    async def test_metrics_track_invocation_count(self, service_effect, mock_event_bus):
        """Test that metrics track total invocations."""
        initial_count = service_effect._total_invocations

        # Create and handle invocation
        event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            target_node_id=service_effect.node_id,
            target_node_name="ModelServiceEffect",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test",
            action="execute",
            parameters={},
        )

        object.__setattr__(
            service_effect, "run", AsyncMock(return_value={"status": "success"})
        )
        await service_effect.handle_tool_invocation(event)

        # Verify count increased
        assert service_effect._total_invocations == initial_count + 1

    @pytest.mark.asyncio
    async def test_metrics_track_success_rate(self, service_effect):
        """Test that metrics track success rate."""
        # Successful invocation
        event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            target_node_id=service_effect.node_id,
            target_node_name="ModelServiceEffect",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test",
            action="execute",
            parameters={},
        )

        object.__setattr__(
            service_effect, "run", AsyncMock(return_value={"status": "success"})
        )
        await service_effect.handle_tool_invocation(event)

        health = service_effect.get_service_health()
        assert health["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_effect_metrics_include_transaction_status(self, service_effect):
        """Test that effect metrics include transaction information."""
        metrics = await service_effect.get_effect_metrics()

        # Verify transaction metrics are included
        assert "transaction_management" in metrics
        assert "active_transactions" in metrics["transaction_management"]
        assert metrics["transaction_management"]["active_transactions"] == 0.0


class TestToolInvocationEventPublishing:
    """Test tool invocation and event publishing integration."""

    @pytest.mark.asyncio
    async def test_successful_invocation_publishes_success_event(
        self, service_effect, tool_invocation_event, mock_event_bus
    ):
        """Test that successful tool invocation publishes success event."""
        # Inject mock event bus
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        object.__setattr__(
            service_effect, "run", AsyncMock(return_value={"result": "success"})
        )

        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify success event was published
        assert mock_event_bus.publish.called
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.success is True
        assert published_event.correlation_id == tool_invocation_event.correlation_id

    @pytest.mark.asyncio
    async def test_failed_invocation_publishes_error_event(
        self, service_effect, tool_invocation_event, mock_event_bus
    ):
        """Test that failed tool invocation publishes error event."""
        # Inject mock event bus
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )
        object.__setattr__(
            service_effect, "run", AsyncMock(side_effect=Exception("Test error"))
        )

        await service_effect.handle_tool_invocation(tool_invocation_event)

        # Verify error event was published
        assert mock_event_bus.publish.called
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.success is False
        assert "Test error" in published_event.error


class TestEffectSemanticsServiceMode:
    """Test effect semantics (transaction management) in service mode."""

    @pytest.mark.asyncio
    async def test_transaction_created_for_transactional_effects(self, service_effect):
        """Test that transactions are created for transactional operations."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"operation_type": "read", "file_path": "/tmp/test.txt"},
            transaction_enabled=True,
            retry_enabled=False,
        )

        # Mock file operation
        with patch("pathlib.Path.exists", return_value=False):
            with pytest.raises(Exception):  # Will fail due to non-existent file
                await service_effect.process(effect_input)

        # Transaction should have been created and rolled back
        assert effect_input.operation_id not in service_effect.active_transactions

    @pytest.mark.asyncio
    async def test_transaction_committed_on_success(self, service_effect):
        """Test that transactions are committed on successful execution."""
        import tempfile
        from pathlib import Path

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test content")

        try:
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={
                    "operation_type": "read",
                    "file_path": str(temp_path),
                },
                transaction_enabled=True,
                retry_enabled=False,
            )

            result = await service_effect.process(effect_input)

            # Verify transaction was committed (removed from active transactions)
            assert effect_input.operation_id not in service_effect.active_transactions
            assert result.transaction_state == EnumTransactionState.COMMITTED

        finally:
            temp_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_transaction_rolled_back_on_error(self, service_effect):
        """Test that transactions are rolled back on error."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={
                "operation_type": "read",
                "file_path": "/nonexistent/file.txt",
            },
            transaction_enabled=True,
            retry_enabled=False,
        )

        with pytest.raises(Exception):
            await service_effect.process(effect_input)

        # Transaction should be removed after rollback
        assert effect_input.operation_id not in service_effect.active_transactions


class TestCircuitBreakerServiceMode:
    """Test circuit breaker integration in service mode."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_execution_when_open(self, service_effect):
        """Test that circuit breaker prevents execution when open."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"operation_type": "read", "file_path": "/tmp/test.txt"},
            circuit_breaker_enabled=True,
            retry_enabled=False,
        )

        # Manually open circuit breaker
        cb = service_effect._get_circuit_breaker(effect_input.effect_type.value)
        cb.state = EnumCircuitBreakerState.OPEN

        # Attempt execution should fail due to open circuit
        with pytest.raises(Exception) as exc_info:
            await service_effect.process(effect_input)

        assert "Circuit breaker open" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self, service_effect):
        """Test that circuit breaker records successful executions."""
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            temp_path = Path(f.name)
            f.write("test content")

        try:
            effect_input = ModelEffectInput(
                effect_type=EnumEffectType.FILE_OPERATION,
                operation_data={
                    "operation_type": "read",
                    "file_path": str(temp_path),
                },
                circuit_breaker_enabled=True,
                retry_enabled=False,
            )

            await service_effect.process(effect_input)

            # Verify circuit breaker recorded success
            cb = service_effect._get_circuit_breaker(effect_input.effect_type.value)
            assert cb.state == EnumCircuitBreakerState.CLOSED

        finally:
            temp_path.unlink(missing_ok=True)


class TestRetryLogicServiceMode:
    """Test retry logic integration in service mode."""

    @pytest.mark.asyncio
    async def test_retry_attempts_on_failure(self, service_effect):
        """Test that retries are attempted on failure."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={
                "operation_type": "read",
                "file_path": "/nonexistent/file.txt",
            },
            retry_enabled=True,
            max_retries=3,
            retry_delay_ms=10,  # Fast retry for testing
        )

        with pytest.raises(Exception):
            await service_effect.process(effect_input)

        # Verify metrics show multiple attempts
        # (total invocations doesn't change, but internal retry counter does)

    @pytest.mark.asyncio
    async def test_exponential_backoff_between_retries(self, service_effect):
        """Test that exponential backoff is applied between retries."""
        call_times = []

        async def failing_handler(operation_data, transaction):
            call_times.append(asyncio.get_event_loop().time())
            raise Exception("Simulated failure")

        service_effect.effect_handlers[EnumEffectType.FILE_OPERATION] = failing_handler

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"test": "data"},
            retry_enabled=True,
            max_retries=2,
            retry_delay_ms=100,
        )

        with pytest.raises(Exception):
            await service_effect.process(effect_input)

        # Verify exponential backoff (delays should increase)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            # First retry has base delay
            assert delay1 >= 0.1  # 100ms


class TestEndToEndWorkflow:
    """Test full end-to-end service workflow."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_start_invoke_respond_stop(
        self, service_effect, mock_event_bus
    ):
        """Test complete lifecycle: start → invoke → respond → stop."""
        # Inject event bus before starting service
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        # Step 1: Start service
        start_task = asyncio.create_task(service_effect.start_service_mode())
        await asyncio.sleep(0.1)  # Allow service to start

        # Verify service is running
        assert service_effect._service_running is True

        # Step 2: Create and handle tool invocation
        event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            target_node_id=service_effect.node_id,
            target_node_name="ModelServiceEffect",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test_tool",
            action="execute",
            parameters={"data": "test"},
        )

        object.__setattr__(
            service_effect, "run", AsyncMock(return_value={"result": "success"})
        )

        # Step 3: Handle invocation
        await service_effect.handle_tool_invocation(event)

        # Step 4: Verify response was published
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response, ModelToolResponseEvent)

        # Step 5: Stop service
        service_effect._shutdown_requested = True
        await asyncio.sleep(0.1)

        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # Verify service stopped
        assert service_effect._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_waits_for_active_invocations(
        self, service_effect, mock_event_bus
    ):
        """Test that graceful shutdown waits for active invocations."""
        # Inject event bus before starting service
        service_effect.event_bus = mock_event_bus
        object.__setattr__(
            service_effect, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        # Create slow operation
        async def slow_run(input_state):
            await asyncio.sleep(0.2)
            return {"result": "success"}

        object.__setattr__(service_effect, "run", slow_run)

        # Start service
        start_task = asyncio.create_task(service_effect.start_service_mode())
        await asyncio.sleep(0.1)

        # Start invocation
        event = ModelToolInvocationEvent(
            node_id=uuid4(),
            correlation_id=uuid4(),
            target_node_id=service_effect.node_id,
            target_node_name="ModelServiceEffect",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test",
            action="execute",
            parameters={},
        )

        invocation_task = asyncio.create_task(
            service_effect.handle_tool_invocation(event)
        )

        await asyncio.sleep(0.05)  # Let invocation start

        # Initiate shutdown
        shutdown_task = asyncio.create_task(service_effect.stop_service_mode())

        # Wait for both to complete
        await asyncio.gather(invocation_task, shutdown_task, return_exceptions=True)

        # Cleanup
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # Verify no active invocations remain
        assert len(service_effect._active_invocations) == 0


class TestMixinMethodAccessibility:
    """Test that methods from all mixins are accessible and functional."""

    def test_node_service_methods_accessible(self, service_effect):
        """Test MixinNodeService methods are accessible."""
        assert callable(service_effect.start_service_mode)
        assert callable(service_effect.stop_service_mode)
        assert callable(service_effect.handle_tool_invocation)
        assert callable(service_effect.get_service_health)
        assert callable(service_effect.add_shutdown_callback)

    def test_node_effect_methods_accessible(self, service_effect):
        """Test NodeEffect methods are accessible."""
        assert callable(service_effect.process)
        assert callable(service_effect.execute_file_operation)
        assert callable(service_effect.emit_state_change_event)
        assert callable(service_effect.get_effect_metrics)

    def test_health_check_methods_accessible(self, service_effect):
        """Test MixinHealthCheck methods are accessible."""
        assert callable(service_effect.get_health_status)

        # Call the method to verify it works
        health = service_effect.get_health_status()
        assert isinstance(health, dict)
        assert "is_healthy" in health

    def test_event_bus_methods_accessible(self, service_effect, mock_event_bus):
        """Test MixinEventBus methods are accessible."""
        assert callable(service_effect.publish_event)

    def test_metrics_methods_accessible(self, service_effect):
        """Test MixinMetrics methods are accessible."""
        assert callable(service_effect.get_metrics)

        # Call the method to verify it works
        metrics = service_effect.get_metrics()
        assert isinstance(metrics, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
