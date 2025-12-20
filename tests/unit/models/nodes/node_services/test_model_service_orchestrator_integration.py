"""
Integration and MRO tests for ModelServiceOrchestrator.

Tests the integration of MixinNodeService with NodeOrchestrator and all mixins:
- MRO correctness validation
- Service mode + EventBus integration (CRITICAL for workflow coordination)
- Service mode + HealthCheck integration
- Service mode + Metrics integration
- Tool invocation + workflow event emission
- Orchestrator semantics (workflow coordination) + service mode
- Workflow lifecycle events through tool invocation
- Full end-to-end workflows
- Mixin initialization order verification
- Super() call propagation
- Method accessibility from all mixins

v0.4.0 Architecture:
- NodeOrchestrator uses workflow-driven pattern with ModelWorkflowDefinition
- Uses MixinWorkflowExecution for execution
- process() method executes workflow steps
- No longer has active_workflows, workflow_states, emitted_actions, condition_functions
"""

import asyncio
import inspect
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.constants.event_types import TOOL_INVOCATION
from omnibase_core.enums.enum_workflow_execution import EnumExecutionMode
from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.services.model_service_orchestrator import (
    ModelServiceOrchestrator,
)
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator


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
def service_orchestrator(mock_container):
    """Create a ModelServiceOrchestrator instance with mocked dependencies."""
    service = ModelServiceOrchestrator(mock_container)
    return service


@pytest.fixture(autouse=True)
async def cleanup_async_tasks():
    """Cleanup any lingering async tasks after each test."""
    yield

    # After test completes, cancel health monitor and service event loop tasks
    current_task = asyncio.current_task()
    pending = [
        t
        for t in asyncio.all_tasks()
        if not t.done()
        and t is not current_task
        and (
            "_health_monitor_loop" in str(t.get_coro())
            or "_service_event_loop" in str(t.get_coro())
        )
    ]

    # Cancel health/service tasks
    for task in pending:
        task.cancel()

    # Wait for cancellation to complete (with timeout to prevent hanging)
    if pending:
        try:
            await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True), timeout=1.0
            )
        except TimeoutError:
            pass  # Tasks didn't cancel in time, but we tried


@pytest.fixture
def tool_invocation_event(service_orchestrator):
    """Create a sample tool invocation event for orchestrator."""
    return ModelToolInvocationEvent(
        node_id=uuid4(),
        correlation_id=uuid4(),
        target_node_id=service_orchestrator.node_id,
        target_node_name="ModelServiceOrchestrator",
        requester_node_id=uuid4(),
        requester_id=uuid4(),
        tool_name="orchestrate_workflow",
        action="execute",
        parameters={
            "workflow_id": str(uuid4()),
            "steps": [
                {
                    "step_id": str(uuid4()),
                    "step_name": "Step 1",
                    "thunks": [],
                }
            ],
            "execution_mode": "sequential",
        },
    )


@pytest.mark.unit
class TestMROCorrectness:
    """Test Method Resolution Order correctness for ModelServiceOrchestrator."""

    def test_mro_order_matches_expected(self, mock_container):
        """Test that MRO follows expected pattern."""
        service = ModelServiceOrchestrator(mock_container)
        mro = inspect.getmro(ModelServiceOrchestrator)

        # Expected MRO (per Python's C3 linearization):
        # ModelServiceOrchestrator -> MixinNodeService -> NodeOrchestrator ->
        # NodeCoreBase -> ABC -> MixinHealthCheck -> MixinEventBus -> (BaseModel/Generic) -> MixinMetrics
        #
        # Note: NodeCoreBase MUST come immediately after NodeOrchestrator because
        # NodeOrchestrator inherits from NodeCoreBase. Python's C3 algorithm ensures
        # a class appears before classes that don't have it as an ancestor.
        expected_classes = [
            ModelServiceOrchestrator,
            MixinNodeService,
            NodeOrchestrator,
            # NodeCoreBase comes here (position 3) because NodeOrchestrator inherits from it
            # ABC comes next (position 4) because NodeCoreBase inherits from it
            # Then the remaining mixins: MixinHealthCheck, MixinEventBus, MixinMetrics
        ]

        # Verify the first 3 positions which are deterministic
        for i, expected_class in enumerate(expected_classes):
            assert mro[i] == expected_class, (
                f"MRO position {i} should be {expected_class.__name__}, "
                f"but got {mro[i].__name__}"
            )

        # Verify NodeCoreBase comes early (due to NodeOrchestrator inheritance)
        nodecorebase_index = next(
            i for i, cls in enumerate(mro) if cls.__name__ == "NodeCoreBase"
        )
        assert nodecorebase_index == 3, (
            f"NodeCoreBase should be at position 3 (after NodeOrchestrator), "
            f"but found at position {nodecorebase_index}"
        )

        # Verify all expected mixins are present in MRO
        mro_names = [cls.__name__ for cls in mro]
        assert "MixinHealthCheck" in mro_names, "MixinHealthCheck missing from MRO"
        assert "MixinEventBus" in mro_names, "MixinEventBus missing from MRO"
        assert "MixinMetrics" in mro_names, "MixinMetrics missing from MRO"

    def test_mro_no_diamond_problem(self, mock_container):
        """Test that MRO resolves diamond inheritance correctly."""
        service = ModelServiceOrchestrator(mock_container)
        mro = inspect.getmro(ModelServiceOrchestrator)

        # Verify no class appears twice in MRO (diamond problem indicator)
        class_names = [cls.__name__ for cls in mro]
        assert len(class_names) == len(set(class_names)), (
            f"MRO contains duplicate classes: {class_names}"
        )

    def test_all_mixins_accessible(self, service_orchestrator):
        """Test that methods from all mixins are accessible."""
        # MixinNodeService methods
        assert hasattr(service_orchestrator, "start_service_mode")
        assert hasattr(service_orchestrator, "stop_service_mode")
        assert hasattr(service_orchestrator, "handle_tool_invocation")
        assert hasattr(service_orchestrator, "get_service_health")

        # NodeOrchestrator methods (v0.4.0 workflow-driven pattern)
        assert hasattr(service_orchestrator, "process")
        assert hasattr(service_orchestrator, "validate_contract")
        assert hasattr(service_orchestrator, "validate_workflow_steps")
        assert hasattr(service_orchestrator, "get_execution_order_for_steps")

        # MixinWorkflowExecution methods (from NodeOrchestrator)
        assert hasattr(service_orchestrator, "execute_workflow_from_contract")
        assert hasattr(service_orchestrator, "validate_workflow_contract")
        assert hasattr(service_orchestrator, "get_workflow_execution_order")
        assert hasattr(service_orchestrator, "create_workflow_steps_from_config")

        # MixinHealthCheck methods
        assert hasattr(service_orchestrator, "get_health_status")

        # MixinEventBus methods
        assert hasattr(service_orchestrator, "publish_event")

        # MixinMetrics methods
        assert hasattr(service_orchestrator, "get_metrics")

    def test_mixin_initialization_order(self, mock_container):
        """Test that all mixins are properly initialized via super().__init__()."""
        service = ModelServiceOrchestrator(mock_container)

        # Verify MixinNodeService initialization
        assert hasattr(service, "_service_running")
        assert service._service_running is False
        assert hasattr(service, "_active_invocations")
        assert isinstance(service._active_invocations, set)

        # Verify NodeOrchestrator initialization (v0.4.0 workflow-driven pattern)
        # NodeOrchestrator now has workflow_definition attribute
        assert hasattr(service, "workflow_definition")
        # workflow_definition starts as None until loaded
        assert service.workflow_definition is None

        # Verify base NodeCoreBase initialization
        assert hasattr(service, "node_id")
        assert isinstance(service.node_id, UUID)
        assert hasattr(service, "container")

    def test_super_call_propagation(self, mock_container):
        """Test that super().__init__() calls propagate through MRO."""
        # Track if NodeOrchestrator.__init__ was called
        original_init = NodeOrchestrator.__init__
        init_called = []

        def tracking_init(self, container):
            """Wrapper that tracks calls and properly passes through to original."""
            init_called.append(True)
            return original_init(self, container)

        with patch.object(NodeOrchestrator, "__init__", tracking_init):
            service = ModelServiceOrchestrator(mock_container)

            # Verify that NodeOrchestrator.__init__ was called via super()
            assert len(init_called) == 1, (
                "NodeOrchestrator.__init__ should be called exactly once via super() chain"
            )


@pytest.mark.unit
class TestServiceModeEventBusIntegration:
    """Test integration between service mode and EventBus mixin (CRITICAL for orchestrators)."""

    @pytest.mark.asyncio
    async def test_service_subscribes_to_tool_invocations(
        self, service_orchestrator, mock_event_bus
    ):
        """Test that service subscribes to TOOL_INVOCATION events on startup."""
        # Mock container to return event bus
        service_orchestrator.container.get_service = Mock(return_value=mock_event_bus)

        # Start service mode
        start_task = asyncio.create_task(service_orchestrator.start_service_mode())
        await asyncio.sleep(0.1)  # Allow startup to proceed

        # Verify subscription
        mock_event_bus.subscribe.assert_called_once()
        call_args = mock_event_bus.subscribe.call_args
        assert call_args[0][1] == TOOL_INVOCATION

        # Stop service
        service_orchestrator._shutdown_requested = True
        await asyncio.sleep(0.1)
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_tool_response_published_via_event_bus(
        self, service_orchestrator, mock_event_bus, tool_invocation_event
    ):
        """Test that tool responses are published via EventBus."""
        # Mock container to return event bus
        service_orchestrator.container.get_service = Mock(return_value=mock_event_bus)

        # Mock the run method to return a result
        async def mock_run(input_state):
            return {"status": "success", "workflow_id": str(uuid4())}

        object.__setattr__(service_orchestrator, "run", mock_run)

        # Handle tool invocation
        await service_orchestrator.handle_tool_invocation(tool_invocation_event)

        # Verify response was published via event bus
        assert mock_event_bus.publish.call_count >= 1

        # Get the published event
        published_event = mock_event_bus.publish.call_args_list[-1][0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.correlation_id == tool_invocation_event.correlation_id
        assert published_event.success is True


@pytest.mark.unit
class TestServiceModeHealthCheckIntegration:
    """Test integration between service mode and HealthCheck mixin."""

    def test_service_health_includes_service_metrics(self, service_orchestrator):
        """Test that get_service_health includes service-specific metrics."""
        health = service_orchestrator.get_service_health()

        # Verify service metrics are included
        assert "status" in health
        assert "uptime_seconds" in health
        assert "active_invocations" in health
        assert "total_invocations" in health
        assert "successful_invocations" in health
        assert "failed_invocations" in health
        assert "success_rate" in health

    def test_service_health_aggregates_node_health(self, service_orchestrator):
        """Test that service health can aggregate with node health."""
        # Get service health
        service_health = service_orchestrator.get_service_health()

        # Get node health (from MixinHealthCheck)
        node_health = service_orchestrator.get_health_status()

        # Both should be available and contain relevant data
        assert service_health["status"] in ["healthy", "unhealthy"]
        assert "node_id" in node_health
        assert "is_healthy" in node_health

    @pytest.mark.asyncio
    async def test_health_reflects_active_invocations(
        self, service_orchestrator, tool_invocation_event
    ):
        """Test that health status reflects active invocations."""

        # Mock run method to simulate long-running operation
        async def slow_run(input_state):
            await asyncio.sleep(0.2)
            return {"status": "success", "workflow_id": str(uuid4())}

        object.__setattr__(service_orchestrator, "run", slow_run)

        # Start invocation in background
        invocation_task = asyncio.create_task(
            service_orchestrator.handle_tool_invocation(tool_invocation_event)
        )

        # Check health while invocation is active
        await asyncio.sleep(0.05)
        health = service_orchestrator.get_service_health()

        # Should show active invocation
        assert health["active_invocations"] >= 1

        # Wait for completion
        await invocation_task

        # Check health after completion
        health_after = service_orchestrator.get_service_health()
        assert health_after["active_invocations"] == 0


@pytest.mark.unit
class TestServiceModeMetricsIntegration:
    """Test integration between service mode and Metrics mixin."""

    @pytest.mark.asyncio
    async def test_metrics_track_invocation_count(
        self, service_orchestrator, mock_event_bus
    ):
        """Test that metrics track total invocations."""
        initial_count = service_orchestrator._total_invocations

        # Create and handle invocation
        event = ModelToolInvocationEvent(
            correlation_id=uuid4(),
            node_id=uuid4(),
            target_node_id=service_orchestrator.node_id,
            target_node_name="ModelServiceOrchestrator",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test",
            action="execute",
            parameters={"workflow_id": str(uuid4()), "steps": []},
        )

        object.__setattr__(
            service_orchestrator,
            "run",
            AsyncMock(return_value={"status": "success", "workflow_id": str(uuid4())}),
        )
        await service_orchestrator.handle_tool_invocation(event)

        # Verify count increased
        assert service_orchestrator._total_invocations == initial_count + 1


@pytest.mark.unit
class TestToolInvocationWorkflowEventEmission:
    """Test tool invocation and workflow event emission integration."""

    @pytest.mark.asyncio
    async def test_successful_workflow_publishes_events(
        self, service_orchestrator, tool_invocation_event, mock_event_bus
    ):
        """Test that successful workflow execution publishes events."""
        # Set event bus directly on service (MixinNodeService uses getattr(self, "event_bus"))
        object.__setattr__(service_orchestrator, "event_bus", mock_event_bus)
        object.__setattr__(
            service_orchestrator, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        object.__setattr__(
            service_orchestrator,
            "run",
            AsyncMock(return_value={"result": "success", "workflow_id": str(uuid4())}),
        )

        await service_orchestrator.handle_tool_invocation(tool_invocation_event)

        # Verify success event was published
        assert mock_event_bus.publish.called
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.success is True
        assert published_event.correlation_id == tool_invocation_event.correlation_id

    @pytest.mark.asyncio
    async def test_failed_workflow_publishes_error_event(
        self, service_orchestrator, tool_invocation_event, mock_event_bus
    ):
        """Test that failed workflow execution publishes error event."""
        # Set event bus directly on service (MixinNodeService uses getattr(self, "event_bus"))
        object.__setattr__(service_orchestrator, "event_bus", mock_event_bus)
        object.__setattr__(
            service_orchestrator, "_get_event_bus", Mock(return_value=mock_event_bus)
        )

        object.__setattr__(
            service_orchestrator,
            "run",
            AsyncMock(side_effect=Exception("Workflow error")),
        )

        await service_orchestrator.handle_tool_invocation(tool_invocation_event)

        # Verify error event was published
        assert mock_event_bus.publish.called
        published_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, ModelToolResponseEvent)
        assert published_event.success is False
        assert "Workflow error" in published_event.error


@pytest.mark.unit
class TestWorkflowDefinitionPattern:
    """Test v0.4.0 workflow-driven orchestrator pattern."""

    def test_workflow_definition_initially_none(self, service_orchestrator):
        """Test that workflow_definition starts as None."""
        assert service_orchestrator.workflow_definition is None

    def test_can_set_workflow_definition(self, service_orchestrator):
        """Test that workflow_definition can be set using object.__setattr__()."""
        # Create a minimal workflow definition mock
        mock_definition = Mock()
        mock_definition.workflow_metadata = Mock()
        mock_definition.execution_graph = Mock()
        mock_definition.coordination_rules = Mock()

        # Use object.__setattr__() to bypass Pydantic validation
        # This is the same pattern used in NodeOrchestrator.__init__
        object.__setattr__(service_orchestrator, "workflow_definition", mock_definition)
        assert service_orchestrator.workflow_definition is mock_definition

    def test_create_workflow_steps_from_config_available(self, service_orchestrator):
        """Test that create_workflow_steps_from_config method is available."""
        assert callable(service_orchestrator.create_workflow_steps_from_config)

        # Test with simple config - note: step_type is required by ModelWorkflowStep
        steps_config = [
            {
                "step_name": "Step 1",
                "step_type": "compute",
            },
        ]

        # This should create ModelWorkflowStep instances
        steps = service_orchestrator.create_workflow_steps_from_config(steps_config)
        assert isinstance(steps, list)
        assert len(steps) == 1

    def test_validate_contract_available(self, service_orchestrator):
        """Test that validate_contract method is available."""
        assert callable(service_orchestrator.validate_contract)


@pytest.mark.unit
class TestEndToEndWorkflow:
    """Test full end-to-end orchestrator service workflow."""

    @pytest.mark.asyncio
    async def test_full_lifecycle_start_invoke_respond_stop(
        self, service_orchestrator, mock_event_bus
    ):
        """Test complete lifecycle: start -> invoke -> respond -> stop."""
        # Mock container to return event bus
        service_orchestrator.container.get_service = Mock(return_value=mock_event_bus)

        # Step 1: Start service
        start_task = asyncio.create_task(service_orchestrator.start_service_mode())
        await asyncio.sleep(0.1)  # Allow service to start

        # Verify service is running
        assert service_orchestrator._service_running is True

        # Step 2: Create and handle tool invocation
        workflow_id = uuid4()
        event = ModelToolInvocationEvent(
            correlation_id=uuid4(),
            node_id=uuid4(),
            target_node_id=service_orchestrator.node_id,
            target_node_name="ModelServiceOrchestrator",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="orchestrate",
            action="execute",
            parameters={
                "workflow_id": str(workflow_id),
                "steps": [
                    {"step_id": str(uuid4()), "step_name": "Step 1", "thunks": []}
                ],
                "execution_mode": "sequential",
            },
        )

        object.__setattr__(
            service_orchestrator,
            "run",
            AsyncMock(
                return_value={"result": "success", "workflow_id": str(workflow_id)}
            ),
        )

        # Step 3: Handle invocation
        await service_orchestrator.handle_tool_invocation(event)

        # Step 4: Verify response was published
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response, ModelToolResponseEvent)

        # Step 5: Stop service
        service_orchestrator._shutdown_requested = True
        await asyncio.sleep(0.1)

        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # Verify service stopped
        assert service_orchestrator._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_graceful_shutdown_waits_for_active_workflows(
        self, service_orchestrator, mock_event_bus
    ):
        """Test that graceful shutdown waits for active workflows."""
        # Mock container to return event bus
        service_orchestrator.container.get_service = Mock(return_value=mock_event_bus)

        # Create slow workflow
        async def slow_run(input_state):
            await asyncio.sleep(0.2)
            return {"result": "success", "workflow_id": str(uuid4())}

        object.__setattr__(service_orchestrator, "run", slow_run)

        # Start service
        start_task = asyncio.create_task(service_orchestrator.start_service_mode())
        await asyncio.sleep(0.1)

        # Start invocation
        event = ModelToolInvocationEvent(
            correlation_id=uuid4(),
            node_id=uuid4(),
            target_node_id=service_orchestrator.node_id,
            target_node_name="ModelServiceOrchestrator",
            requester_node_id=uuid4(),
            requester_id=uuid4(),
            tool_name="test",
            action="execute",
            parameters={"workflow_id": str(uuid4()), "steps": []},
        )

        invocation_task = asyncio.create_task(
            service_orchestrator.handle_tool_invocation(event)
        )

        await asyncio.sleep(0.05)  # Let invocation start

        # Initiate shutdown
        shutdown_task = asyncio.create_task(service_orchestrator.stop_service_mode())

        # Wait for both to complete
        await asyncio.gather(invocation_task, shutdown_task, return_exceptions=True)

        # Cleanup
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # Verify no active invocations remain
        assert len(service_orchestrator._active_invocations) == 0


@pytest.mark.unit
class TestMixinMethodAccessibility:
    """Test that methods from all mixins are accessible and functional."""

    def test_node_service_methods_accessible(self, service_orchestrator):
        """Test MixinNodeService methods are accessible."""
        assert callable(service_orchestrator.start_service_mode)
        assert callable(service_orchestrator.stop_service_mode)
        assert callable(service_orchestrator.handle_tool_invocation)
        assert callable(service_orchestrator.get_service_health)
        assert callable(service_orchestrator.add_shutdown_callback)

    def test_node_orchestrator_methods_accessible(self, service_orchestrator):
        """Test NodeOrchestrator methods are accessible (v0.4.0 workflow-driven)."""
        assert callable(service_orchestrator.process)
        assert callable(service_orchestrator.validate_contract)
        assert callable(service_orchestrator.validate_workflow_steps)
        assert callable(service_orchestrator.get_execution_order_for_steps)

        # MixinWorkflowExecution methods
        assert callable(service_orchestrator.execute_workflow_from_contract)
        assert callable(service_orchestrator.validate_workflow_contract)
        assert callable(service_orchestrator.get_workflow_execution_order)
        assert callable(service_orchestrator.create_workflow_steps_from_config)

    def test_health_check_methods_accessible(self, service_orchestrator):
        """Test MixinHealthCheck methods are accessible."""
        assert callable(service_orchestrator.get_health_status)

        # Call the method to verify it works
        health = service_orchestrator.get_health_status()
        assert isinstance(health, dict)
        assert "is_healthy" in health

    def test_event_bus_methods_accessible(self, service_orchestrator, mock_event_bus):
        """Test MixinEventBus methods are accessible."""
        assert callable(service_orchestrator.publish_event)

    def test_metrics_methods_accessible(self, service_orchestrator):
        """Test MixinMetrics methods are accessible."""
        assert callable(service_orchestrator.get_metrics)

        # Call the method to verify it works
        metrics = service_orchestrator.get_metrics()
        assert isinstance(metrics, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
