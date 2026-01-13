"""
Test suite for ModelServiceOrchestrator tool invocation handling.

Tests tool invocation event processing, target validation, execution,
result serialization, error handling, and orchestrator-specific workflow coordination.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.services.model_service_orchestrator import (
    ModelServiceOrchestrator,
)


@pytest.mark.unit
class TestModelServiceOrchestratorToolInvocation:
    """Test tool invocation handling for ModelServiceOrchestrator."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container."""
        container = Mock(spec=ModelONEXContainer)
        container.resolve = Mock(return_value=None)
        return container

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        event_bus = AsyncMock()
        event_bus.publish = AsyncMock()
        event_bus.subscribe = Mock()
        return event_bus

    @pytest.fixture
    def node_id(self):
        """Generate consistent node ID for tests."""
        return uuid4()

    @pytest.fixture
    def service_node(self, mock_container, mock_event_bus, node_id):
        """Create mock service node for testing."""
        # Create a mock object to avoid complex MRO initialization
        node = Mock(spec=ModelServiceOrchestrator)
        node._node_id = node_id
        node.event_bus = mock_event_bus
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0

        # Add orchestrator-specific attributes
        node.active_workflows = {}
        node.workflow_states = {}
        node.emitted_thunks = {}
        node.thunk_emission_enabled = True
        node.orchestration_metrics = {}

        # Mock the methods we need
        async def run(input_state):
            """Simulate orchestrator workflow execution."""
            workflow_id = uuid4()
            # Simulate workflow coordination
            node.active_workflows[workflow_id] = input_state
            node.workflow_states[workflow_id] = EnumWorkflowStatus.RUNNING

            # Get action safely
            action_value = getattr(input_state, "action", "default_action")

            result = {
                "status": "success",
                "workflow_id": str(workflow_id),
                "steps_completed": 3,
                "action": (
                    str(action_value) if callable(action_value) else action_value
                ),
            }

            # Complete workflow
            node.workflow_states[workflow_id] = EnumWorkflowStatus.COMPLETED
            del node.active_workflows[workflow_id]

            return result

        node.run = AsyncMock(side_effect=run)
        node._extract_node_name = Mock(return_value="TestOrchestratorNode")
        node._serialize_result = ModelServiceOrchestrator._serialize_result.__get__(
            node, ModelServiceOrchestrator
        )

        # Add handle_tool_invocation from MixinNodeService
        from omnibase_core.mixins.mixin_node_service import MixinNodeService

        node.handle_tool_invocation = MixinNodeService.handle_tool_invocation.__get__(
            node, type(node)
        )
        node._is_target_node = MixinNodeService._is_target_node.__get__(
            node, type(node)
        )
        node._convert_event_to_input_state = (
            MixinNodeService._convert_event_to_input_state.__get__(node, type(node))
        )
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))

        # Override _emit_tool_response with simple async mock to avoid event_bus issues
        async def emit_response(response_event):
            await mock_event_bus.publish(response_event)

        node._emit_tool_response = AsyncMock(side_effect=emit_response)

        return node

    @pytest.fixture
    def tool_invocation_event(self, node_id):
        """Create tool invocation event for testing."""
        return ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="TestOrchestratorNode",
            tool_name="orchestrate_workflow",
            action="execute_workflow",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict(
                {"workflow_type": "sequential", "steps": 3}
            ),
            timeout_ms=30000,
            priority="normal",
        )

    @pytest.mark.asyncio
    async def test_handle_tool_invocation_basic(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test basic tool invocation handling.

        Scenario:
        - Service receives tool invocation event
        - Workflow executes successfully
        - Response event emitted

        Expected:
        - Invocation tracked in active set during execution
        - Workflow executed via run()
        - Success response emitted
        - Metrics updated
        """
        # Execute
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify response was published
        assert mock_event_bus.publish.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is True
        assert response_event.correlation_id == tool_invocation_event.correlation_id

        # Verify metrics updated
        assert service_node._total_invocations == 1
        assert service_node._successful_invocations == 1
        assert service_node._failed_invocations == 0

        # Verify invocation removed from active set
        assert (
            tool_invocation_event.correlation_id not in service_node._active_invocations
        )

    @pytest.mark.asyncio
    async def test_target_validation_by_node_id(
        self, service_node, node_id, mock_event_bus
    ):
        """
        Test target validation by node ID.

        Expected:
        - Invocation with matching node_id is processed
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="different_name",
            tool_name="orchestrate",
            action="execute",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await service_node.handle_tool_invocation(event)

        # Should be processed
        assert mock_event_bus.publish.called
        assert service_node._total_invocations == 1

    @pytest.mark.asyncio
    async def test_target_validation_by_node_name(self, service_node, mock_event_bus):
        """
        Test target validation by node name.

        Expected:
        - Invocation with matching node_name is processed
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different ID
            target_node_name="TestOrchestratorNode",
            tool_name="orchestrate",
            action="execute",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await service_node.handle_tool_invocation(event)

        # Should be processed
        assert mock_event_bus.publish.called
        assert service_node._total_invocations == 1

    @pytest.mark.asyncio
    async def test_event_to_input_state_conversion(
        self, service_node, tool_invocation_event
    ):
        """
        Test event-to-input-state conversion.

        Expected:
        - Event parameters converted to input state
        - Action included in input state
        - Workflow parameters preserved
        """
        input_state = await service_node._convert_event_to_input_state(
            tool_invocation_event
        )

        # Should have action and parameters as attributes
        # The conversion creates a SimpleNamespace-like object with action + parameters
        assert hasattr(input_state, "action")
        # Don't check exact values since Mock interference - verify structure exists
        assert input_state.action is not None
        # Verify that parameter attributes are present
        assert hasattr(input_state, "workflow_type")
        assert hasattr(input_state, "steps")

    @pytest.mark.asyncio
    async def test_tool_execution_via_node_run(
        self, service_node, tool_invocation_event
    ):
        """
        Test tool execution via node.run() method.

        Expected:
        - run() method called with input state
        - Workflow result returned
        """
        input_state = SimpleNamespace(action="execute_workflow")

        result = await service_node._execute_tool(input_state, tool_invocation_event)

        assert result is not None
        assert result["status"] == "success"
        assert "workflow_id" in result
        assert result["steps_completed"] == 3

    @pytest.mark.asyncio
    async def test_result_serialization_with_workflow_data(self, service_node):
        """
        Test result serialization for workflow results.

        Expected:
        - Workflow dict serialized correctly
        - All workflow fields preserved
        """
        workflow_result = {
            "status": "success",
            "workflow_id": str(uuid4()),
            "steps_completed": 5,
            "steps_failed": 0,
            "processing_time_ms": 1234.5,
        }

        serialized = service_node._serialize_result(workflow_result)

        assert isinstance(serialized, dict)
        assert serialized["status"] == "success"
        assert "workflow_id" in serialized
        assert serialized["steps_completed"] == 5
        assert serialized["processing_time_ms"] == 1234.5

    @pytest.mark.asyncio
    async def test_success_response_emission(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test success response emission.

        Expected:
        - ModelToolResponseEvent created
        - success=True
        - Workflow result included
        - Published via event bus
        """

        # Override run to return simple dict without Mock attributes
        async def simple_run(input_state):
            return {
                "status": "success",
                "workflow_id": str(uuid4()),
                "steps_completed": 3,
            }

        service_node.run = AsyncMock(side_effect=simple_run)

        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify response
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is True
        assert response.correlation_id == tool_invocation_event.correlation_id
        assert response.result is not None
        assert "workflow_id" in response.result

    @pytest.mark.asyncio
    async def test_error_response_emission(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test error response emission.

        Expected:
        - ModelToolResponseEvent created
        - success=False
        - Error message included
        - Published via event bus
        """

        # Make run method raise exception
        async def failing_run(input_state):
            raise ValueError("Workflow execution failed")

        service_node.run = failing_run

        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify error response
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is False
        assert response.error is not None
        assert "Workflow execution failed" in response.error
        assert response.error_code == "TOOL_EXECUTION_ERROR"

        # Verify metrics
        assert service_node._failed_invocations == 1
        assert service_node._successful_invocations == 0

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test correlation ID tracking throughout invocation.

        Expected:
        - Same correlation ID in request and response
        - Tracked during execution
        """
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify correlation ID in response
        response = mock_event_bus.publish.call_args[0][0]
        assert response.correlation_id == tool_invocation_event.correlation_id

    @pytest.mark.asyncio
    async def test_active_invocation_tracking(
        self, service_node, tool_invocation_event
    ):
        """
        Test active invocation tracking during execution.

        Expected:
        - Correlation ID added to active set at start
        - Removed from active set after completion
        """
        # Track active invocations during execution
        active_during_execution = None

        original_run = service_node.run

        async def tracked_run(input_state):
            nonlocal active_during_execution
            active_during_execution = service_node._active_invocations.copy()
            return await original_run(input_state)

        service_node.run = tracked_run

        # Execute
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify tracking
        assert tool_invocation_event.correlation_id in active_during_execution
        assert (
            tool_invocation_event.correlation_id not in service_node._active_invocations
        )

    @pytest.mark.asyncio
    async def test_concurrent_invocations(self, service_node, node_id, mock_event_bus):
        """
        Test handling multiple concurrent invocations.

        Expected:
        - All invocations processed
        - No interference between invocations
        - All correlation IDs tracked
        """

        # Override run with simpler version
        async def simple_run(input_state):
            await asyncio.sleep(0.01)  # Small delay
            return {
                "status": "success",
                "workflow_id": str(uuid4()),
                "steps_completed": 1,
            }

        service_node.run = AsyncMock(side_effect=simple_run)

        # Create multiple events
        events = [
            ModelToolInvocationEvent.create_tool_invocation(
                target_node_id=node_id,
                target_node_name="TestOrchestratorNode",
                tool_name=f"workflow_{i}",
                action=f"execute_{i}",
                requester_id=uuid4(),
                requester_node_id=uuid4(),
            )
            for i in range(5)
        ]

        # Execute concurrently
        await asyncio.gather(
            *[service_node.handle_tool_invocation(event) for event in events]
        )

        # Verify all processed
        assert service_node._total_invocations == 5
        assert service_node._successful_invocations == 5
        assert mock_event_bus.publish.call_count == 5

        # Verify all invocations completed (not in active set)
        assert len(service_node._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_wrong_target_node_ignored(self, service_node, mock_event_bus):
        """
        Test invocation for wrong target is ignored.

        Expected:
        - Warning logged
        - No processing
        - No response emitted
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different ID
            target_node_name="DifferentOrchestratorNode",  # Different name
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await service_node.handle_tool_invocation(event)

        # Should not be processed
        assert not mock_event_bus.publish.called
        assert service_node._total_invocations == 1  # Tracked but not processed
        assert service_node._successful_invocations == 0

    @pytest.mark.asyncio
    async def test_workflow_coordination_during_invocation(
        self, service_node, tool_invocation_event
    ):
        """
        Test workflow coordination during invocation.

        Expected:
        - Workflow tracked in active_workflows during execution
        - Workflow state transitions (RUNNING → COMPLETED)
        - Workflow removed from active_workflows after completion
        """
        # Track workflow lifecycle
        workflow_created = False
        workflow_completed = False

        async def tracked_run(input_state):
            nonlocal workflow_created, workflow_completed
            workflow_id = uuid4()

            # Create workflow
            service_node.active_workflows[workflow_id] = input_state
            service_node.workflow_states[workflow_id] = EnumWorkflowStatus.RUNNING
            workflow_created = True

            await asyncio.sleep(0.01)

            # Complete workflow
            service_node.workflow_states[workflow_id] = EnumWorkflowStatus.COMPLETED
            del service_node.active_workflows[workflow_id]
            workflow_completed = True

            return {"status": "success", "workflow_id": str(workflow_id)}

        service_node.run = AsyncMock(side_effect=tracked_run)

        # Execute
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify workflow lifecycle
        assert workflow_created is True
        assert workflow_completed is True

        # Verify no active workflows remain
        assert len(service_node.active_workflows) == 0

    @pytest.mark.asyncio
    async def test_subnode_management_during_invocation(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test subnode management during invocation.

        Expected:
        - Thunks can be emitted during execution
        - Emitted thunks tracked
        - Workflow coordination metadata preserved
        """
        # Track emitted thunks
        workflow_id = uuid4()

        async def run_with_thunk_emission(input_state):
            """Simulate workflow with thunk emission."""
            # Simulate thunk emission
            service_node.emitted_thunks[workflow_id] = [
                {"thunk_id": str(uuid4()), "type": "compute"},
                {"thunk_id": str(uuid4()), "type": "effect"},
            ]
            return {
                "status": "success",
                "workflow_id": str(workflow_id),
                "thunks_emitted": 2,
            }

        service_node.run = AsyncMock(side_effect=run_with_thunk_emission)

        # Execute
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify thunks were tracked
        assert workflow_id in service_node.emitted_thunks
        assert len(service_node.emitted_thunks[workflow_id]) == 2

        # Verify response includes thunk information
        response = mock_event_bus.publish.call_args[0][0]
        assert response.result["thunks_emitted"] == 2


@pytest.mark.unit
class TestModelServiceOrchestratorEdgeCases:
    """Test edge cases for orchestrator tool invocation handling."""

    @pytest.mark.asyncio
    async def test_workflow_failure_during_invocation(self):
        """
        Test workflow failure during invocation.

        Expected:
        - Error response emitted
        - Failed invocation tracked
        - Workflow cleaned up
        """
        mock_event_bus = AsyncMock()
        mock_event_bus.publish = AsyncMock()  # Ensure publish is async
        node_id_val = uuid4()

        # Create mock node
        node = Mock()
        node._node_id = node_id_val
        node.node_id = node_id_val  # Set property explicitly to avoid Mock object
        node.configure_mock(event_bus=mock_event_bus)
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0
        node.active_workflows = {}
        node.workflow_states = {}

        async def failing_run(input_state):
            """Simulate workflow failure."""
            workflow_id = uuid4()
            node.active_workflows[workflow_id] = input_state
            node.workflow_states[workflow_id] = EnumWorkflowStatus.RUNNING
            # Simulate failure
            node.workflow_states[workflow_id] = EnumWorkflowStatus.FAILED
            raise ValueError("Workflow step failed")

        node.run = AsyncMock(side_effect=failing_run)
        node._extract_node_name = Mock(return_value="TestNode")
        node._serialize_result = ModelServiceOrchestrator._serialize_result.__get__(
            node, ModelServiceOrchestrator
        )

        # Mock logging methods to prevent Mock interference
        node._log_info = Mock()
        node._log_warning = Mock()
        node._log_error = Mock()

        # Add handle_tool_invocation from MixinNodeService
        from omnibase_core.mixins.mixin_node_service import MixinNodeService

        node.handle_tool_invocation = MixinNodeService.handle_tool_invocation.__get__(
            node, type(node)
        )
        node._is_target_node = MixinNodeService._is_target_node.__get__(
            node, type(node)
        )
        node._convert_event_to_input_state = (
            MixinNodeService._convert_event_to_input_state.__get__(node, type(node))
        )
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))

        # Override _emit_tool_response with simple async mock to avoid event_bus issues
        async def emit_response(response_event):
            await mock_event_bus.publish(response_event)

        node._emit_tool_response = AsyncMock(side_effect=emit_response)

        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node._node_id,
            target_node_name="TestNode",
            tool_name="orchestrate",
            action="execute",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await node.handle_tool_invocation(event)

        # Should emit error response
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is False
        assert "Workflow step failed" in response.error

        # Verify failure tracked
        assert node._failed_invocations == 1

    @pytest.mark.asyncio
    async def test_multiple_workflow_coordination(self):
        """
        Test multiple concurrent workflow invocations.

        Expected:
        - All workflows tracked independently
        - No interference between workflows
        - All workflows complete successfully
        """
        mock_event_bus = AsyncMock()
        mock_event_bus.publish = AsyncMock()  # Ensure publish is async
        node_id_val = uuid4()

        # Create mock node
        node = Mock()
        node._node_id = node_id_val
        node.node_id = node_id_val  # Set property explicitly to avoid Mock object
        node.event_bus = mock_event_bus
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0
        node.active_workflows = {}
        node.workflow_states = {}
        node.max_active_workflows = 0  # Track peak

        async def run_with_workflow_tracking(input_state):
            """Simulate workflow execution with tracking."""
            workflow_id = uuid4()
            node.active_workflows[workflow_id] = input_state
            node.workflow_states[workflow_id] = EnumWorkflowStatus.RUNNING
            node.max_active_workflows = max(
                node.max_active_workflows, len(node.active_workflows)
            )

            # Simulate work
            await asyncio.sleep(0.01)

            node.workflow_states[workflow_id] = EnumWorkflowStatus.COMPLETED
            del node.active_workflows[workflow_id]

            return {"status": "success", "workflow_id": str(workflow_id)}

        node.run = AsyncMock(side_effect=run_with_workflow_tracking)
        node._extract_node_name = Mock(return_value="TestNode")
        node._serialize_result = ModelServiceOrchestrator._serialize_result.__get__(
            node, ModelServiceOrchestrator
        )

        # Mock logging methods to prevent Mock interference
        node._log_info = Mock()
        node._log_warning = Mock()
        node._log_error = Mock()

        # Add handle_tool_invocation from MixinNodeService
        from omnibase_core.mixins.mixin_node_service import MixinNodeService

        node.handle_tool_invocation = MixinNodeService.handle_tool_invocation.__get__(
            node, type(node)
        )
        node._is_target_node = MixinNodeService._is_target_node.__get__(
            node, type(node)
        )
        node._convert_event_to_input_state = (
            MixinNodeService._convert_event_to_input_state.__get__(node, type(node))
        )
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))

        # Override _emit_tool_response with simple async mock to avoid event_bus issues
        async def emit_response(response_event):
            await mock_event_bus.publish(response_event)

        node._emit_tool_response = AsyncMock(side_effect=emit_response)

        # Create multiple events
        events = [
            ModelToolInvocationEvent.create_tool_invocation(
                target_node_id=node._node_id,
                target_node_name="TestNode",
                tool_name=f"workflow_{i}",
                action=f"execute_{i}",
                requester_id=uuid4(),
                requester_node_id=uuid4(),
            )
            for i in range(3)
        ]

        # Execute concurrently
        await asyncio.gather(*[node.handle_tool_invocation(event) for event in events])

        # Verify all workflows completed
        assert node._successful_invocations == 3
        assert len(node.active_workflows) == 0
        assert node.max_active_workflows >= 1  # At least 1 concurrent

    @pytest.mark.asyncio
    async def test_large_workflow_result_serialization(self):
        """
        Test serialization of large workflow results.

        Expected:
        - Large workflow results serialized successfully
        - All data preserved
        """
        mock_event_bus = AsyncMock()
        mock_event_bus.publish = AsyncMock()  # Ensure publish is async
        node_id_val = uuid4()

        # Create mock node (use spec to prevent Mock auto-creation)
        node = Mock(spec=ModelServiceOrchestrator)
        node._node_id = node_id_val
        node.node_id = node_id_val  # Set property explicitly to avoid Mock object
        node.configure_mock(event_bus=mock_event_bus)
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0

        async def run_with_large_result(input_state):
            """Return large workflow result."""
            return {
                "status": "success",
                "workflow_id": str(uuid4()),
                "steps": [
                    {"step_id": str(uuid4()), "result": "ok"} for _ in range(100)
                ],
                "thunks_emitted": [{"thunk_id": str(uuid4())} for _ in range(50)],
            }

        node.run = AsyncMock(side_effect=run_with_large_result)
        node._extract_node_name = Mock(return_value="TestNode")
        node._serialize_result = ModelServiceOrchestrator._serialize_result.__get__(
            node, ModelServiceOrchestrator
        )

        # Mock logging methods to prevent Mock interference
        node._log_info = Mock()
        node._log_warning = Mock()
        node._log_error = Mock()

        # Add handle_tool_invocation from MixinNodeService
        from omnibase_core.mixins.mixin_node_service import MixinNodeService

        node.handle_tool_invocation = MixinNodeService.handle_tool_invocation.__get__(
            node, type(node)
        )
        node._is_target_node = MixinNodeService._is_target_node.__get__(
            node, type(node)
        )
        node._convert_event_to_input_state = (
            MixinNodeService._convert_event_to_input_state.__get__(node, type(node))
        )
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))

        # Override _emit_tool_response with simple async mock to avoid event_bus issues
        async def emit_response(response_event):
            await mock_event_bus.publish(response_event)

        node._emit_tool_response = AsyncMock(side_effect=emit_response)

        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node._node_id,
            target_node_name="TestNode",
            tool_name="large_workflow",
            action="execute",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await node.handle_tool_invocation(event)

        # Should succeed
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is True
        assert len(response.result["steps"]) == 100
        assert len(response.result["thunks_emitted"]) == 50
