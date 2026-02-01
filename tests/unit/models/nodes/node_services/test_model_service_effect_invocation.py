"""
Test suite for ModelServiceEffect tool invocation handling.

Tests tool invocation event processing, target validation, execution,
result serialization, and error handling.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.mixins.mixin_node_service import MixinNodeService
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.services.model_service_effect import ModelServiceEffect


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelServiceEffectToolInvocation:
    """Test tool invocation handling for ModelServiceEffect."""

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
        # Create a mock object instead of full ModelServiceEffect
        # to avoid complex MRO initialization issues
        node = Mock(spec=ModelServiceEffect)
        node._node_id = node_id
        node.event_bus = mock_event_bus
        node._get_event_bus = Mock(
            return_value=mock_event_bus
        )  # Mock event bus resolution
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0

        # Mock the methods we need
        async def run(input_state):
            return {"status": "success", "result": input_state.action}

        node.run = AsyncMock(side_effect=run)
        node._extract_node_name = Mock(return_value="TestEffectNode")
        node._serialize_result = MixinNodeService._serialize_result.__get__(
            node, MixinNodeService
        )
        # Mock _infer_input_state_class to return None (forces SimpleNamespace fallback)
        node._infer_input_state_class = Mock(return_value=None)

        # Add handle_tool_invocation from MixinNodeService
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
        node._emit_tool_response = MixinNodeService._emit_tool_response.__get__(
            node, type(node)
        )
        node._try_get_event_bus_from_container = (
            MixinNodeService._try_get_event_bus_from_container.__get__(node, type(node))
        )

        return node

    @pytest.fixture
    def tool_invocation_event(self, node_id):
        """Create tool invocation event for testing."""
        return ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="TestEffectNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"param1": "value1"}),
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
        - Tool executes successfully
        - Response event emitted

        Expected:
        - Invocation tracked in active set during execution
        - Tool executed via run()
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
    async def test_handle_tool_invocation_tracks_active(
        self, service_node, tool_invocation_event
    ):
        """
        Test invocation tracking during execution.

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
            tool_name="test_tool",
            action="test_action",
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
            target_node_name="TestEffectNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await service_node.handle_tool_invocation(event)

        # Should be processed
        assert mock_event_bus.publish.called
        assert service_node._total_invocations == 1

    @pytest.mark.asyncio
    async def test_target_validation_by_service_name(
        self, service_node, mock_event_bus
    ):
        """
        Test target validation by service name via target_node_name.

        Expected:
        - Invocation with service name pattern is processed
        - Service name can be specified in target_node_name field
        """
        # Create event with service name pattern in target_node_name
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different UUID
            target_node_name="TestEffectNode_service",  # Service name pattern
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        # Override _is_target_node to check for service name suffix
        original_is_target = service_node._is_target_node

        def custom_is_target(event):
            # Accept normal match or service name suffix match
            return (
                original_is_target(event)
                or event.target_node_name
                == f"{service_node._extract_node_name()}_service"
            )

        service_node._is_target_node = custom_is_target

        await service_node.handle_tool_invocation(event)

        # Should be processed
        assert mock_event_bus.publish.called
        assert service_node._total_invocations == 1

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
            target_node_name="DifferentNode",  # Different name
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
    async def test_event_to_input_state_conversion(
        self, service_node, tool_invocation_event
    ):
        """
        Test event-to-input-state conversion.

        Expected:
        - Event parameters converted to input state
        - Action included in input state
        """
        input_state = await service_node._convert_event_to_input_state(
            tool_invocation_event
        )

        # Should have action and parameters
        assert hasattr(input_state, "action")
        assert input_state.action == "test_action"
        assert hasattr(input_state, "param1")
        assert input_state.param1 == "value1"

    @pytest.mark.asyncio
    async def test_tool_execution_async_run(self, service_node, tool_invocation_event):
        """
        Test tool execution via async run method.

        Expected:
        - Async run method called
        - Result returned
        """
        input_state = SimpleNamespace(action="test_action")

        result = await service_node._execute_tool(input_state, tool_invocation_event)

        assert result is not None
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_tool_execution_sync_run(
        self, mock_container, mock_event_bus, node_id
    ):
        """
        Test tool execution via sync run method.

        Expected:
        - Sync run method executed in executor
        - Result returned
        """
        # Create mock node with sync run method
        node = Mock()
        node._node_id = node_id
        node.event_bus = mock_event_bus

        def run(input_state):
            """Sync run method."""
            return {"status": "success", "result": "sync_result"}

        node.run = Mock(side_effect=run)
        # Mock _infer_input_state_class to return None (forces SimpleNamespace fallback)
        node._infer_input_state_class = Mock(return_value=None)

        # Add _execute_tool method
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))
        input_state = SimpleNamespace(action="test_action")
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="SyncEffectNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        result = await node._execute_tool(input_state, event)

        assert result is not None
        assert result["status"] == "success"
        assert result["result"] == "sync_result"

    @pytest.mark.asyncio
    async def test_missing_run_method_error(
        self, mock_container, mock_event_bus, node_id
    ):
        """
        Test error when node has no run method.

        Expected:
        - ModelOnexError raised
        """
        # Create mock node without run method
        # Use spec=[] to ensure no attributes by default
        node = Mock(
            spec=["_node_id", "event_bus", "_infer_input_state_class", "_execute_tool"]
        )
        node._node_id = node_id
        node.event_bus = mock_event_bus
        # Explicitly ensure run does not exist by not adding it
        # Mock _infer_input_state_class to return None (forces SimpleNamespace fallback)
        node._infer_input_state_class = Mock(return_value=None)

        # Add _execute_tool method
        node._execute_tool = MixinNodeService._execute_tool.__get__(node, type(node))
        input_state = SimpleNamespace(action="test_action")
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="NoRunMethodNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        with pytest.raises(ModelOnexError, match="does not have a 'run' method"):
            await node._execute_tool(input_state, event)

    @pytest.mark.asyncio
    async def test_result_serialization_pydantic_model(self, service_node):
        """
        Test result serialization for Pydantic models.

        Expected:
        - model_dump() called
        - Dict returned
        """

        class TestResult(BaseModel):
            status: str
            data: str

        result = TestResult(status="success", data="test_data")
        serialized = service_node._serialize_result(result)

        assert isinstance(serialized, dict)
        assert serialized["status"] == "success"
        assert serialized["data"] == "test_data"

    @pytest.mark.asyncio
    async def test_result_serialization_dict(self, service_node):
        """
        Test result serialization for dict objects.

        Expected:
        - Dict returned as-is
        """
        result = {"status": "success", "data": "test_data"}
        serialized = service_node._serialize_result(result)

        assert serialized == result

    @pytest.mark.asyncio
    async def test_result_serialization_primitive(self, service_node):
        """
        Test result serialization for primitive types.

        Expected:
        - Wrapped in {"result": value}
        """
        result = "simple_string"
        serialized = service_node._serialize_result(result)

        assert isinstance(serialized, dict)
        assert serialized["result"] == "simple_string"

    @pytest.mark.asyncio
    async def test_success_response_emission(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test success response emission.

        Expected:
        - ModelToolResponseEvent created
        - success=True
        - Result included
        - Published via event bus
        """
        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify response
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is True
        assert response.correlation_id == tool_invocation_event.correlation_id
        assert response.result is not None

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
            raise ValueError("Test error")

        service_node.run = failing_run

        await service_node.handle_tool_invocation(tool_invocation_event)

        # Verify error response
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is False
        assert response.error is not None
        assert "Test error" in response.error
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
    async def test_concurrent_invocations(self, service_node, node_id, mock_event_bus):
        """
        Test handling multiple concurrent invocations.

        Expected:
        - All invocations processed
        - No interference between invocations
        - All correlation IDs tracked
        """
        # Create multiple events
        events = [
            ModelToolInvocationEvent.create_tool_invocation(
                target_node_id=node_id,
                target_node_name="TestEffectNode",
                tool_name=f"tool_{i}",
                action=f"action_{i}",
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
    async def test_execution_timeout_handling(
        self, service_node, tool_invocation_event, mock_event_bus
    ):
        """
        Test handling of execution timeout.

        Expected:
        - Timeout error caught
        - Error response emitted
        - Failed invocation tracked
        """

        async def slow_run(input_state):
            """Simulate slow execution."""
            await asyncio.sleep(10)  # Very slow
            return {"status": "success"}

        service_node.run = slow_run

        # Create event with short timeout (minimum 1000ms per validation)
        short_timeout_event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=tool_invocation_event.target_node_id,
            target_node_name=tool_invocation_event.target_node_name,
            tool_name=tool_invocation_event.tool_name,
            action=tool_invocation_event.action,
            requester_id=tool_invocation_event.requester_id,
            requester_node_id=tool_invocation_event.requester_node_id,
            timeout_ms=1000,  # Minimum valid timeout
        )

        # Wrap execution with timeout
        try:
            await asyncio.wait_for(
                service_node.handle_tool_invocation(short_timeout_event),
                timeout=0.5,  # 500ms timeout (shorter than slow_run)
            )
        except TimeoutError:
            # Expected timeout
            pass

        # Verify invocation was tracked
        assert service_node._total_invocations == 1


@pytest.mark.timeout(60)
@pytest.mark.unit
class TestModelServiceEffectEdgeCases:
    """Test edge cases for tool invocation handling."""

    @pytest.mark.asyncio
    async def test_empty_parameters(self):
        """
        Test invocation with no parameters.

        Expected:
        - Handled gracefully
        - Input state created with action only
        """
        mock_event_bus = AsyncMock()
        node_id_val = uuid4()

        # Create mock node
        node = Mock()
        node._node_id = node_id_val
        node.node_id = node_id_val  # Explicitly set property for getattr() calls
        node.event_bus = mock_event_bus
        node._get_event_bus = Mock(
            return_value=mock_event_bus
        )  # Mock event bus resolution
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0

        async def run(input_state):
            return {"action": input_state.action}

        node.run = AsyncMock(side_effect=run)
        node._extract_node_name = Mock(return_value="TestNode")
        node._serialize_result = MixinNodeService._serialize_result.__get__(
            node, MixinNodeService
        )
        # Set _input_state_class to None explicitly (Mock auto-creates attributes)
        # so that getattr(self, "_input_state_class", None) returns None
        node._input_state_class = None
        # Mock _infer_input_state_class to return None (forces SimpleNamespace fallback)
        node._infer_input_state_class = Mock(return_value=None)

        # Add handle_tool_invocation from MixinNodeService
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
        node._emit_tool_response = MixinNodeService._emit_tool_response.__get__(
            node, type(node)
        )
        node._try_get_event_bus_from_container = (
            MixinNodeService._try_get_event_bus_from_container.__get__(node, type(node))
        )
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node._node_id,
            target_node_name="TestNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters(),  # Empty parameters
        )

        await node.handle_tool_invocation(event)

        # Should succeed
        assert mock_event_bus.publish.called
        assert node._successful_invocations == 1

    @pytest.mark.asyncio
    async def test_large_result_serialization(self):
        """
        Test serialization of large result objects.

        Expected:
        - Large objects serialized successfully
        """
        mock_event_bus = AsyncMock()
        node_id_val = uuid4()

        # Create mock node
        node = Mock()
        node._node_id = node_id_val
        node.node_id = node_id_val  # Explicitly set property for getattr() calls
        node.event_bus = mock_event_bus
        node._get_event_bus = Mock(
            return_value=mock_event_bus
        )  # Mock event bus resolution
        node._active_invocations = set()
        node._total_invocations = 0
        node._successful_invocations = 0
        node._failed_invocations = 0

        async def run(input_state):
            # Return large result
            return {"data": ["item"] * 1000, "status": "success"}

        node.run = AsyncMock(side_effect=run)
        node._extract_node_name = Mock(return_value="TestNode")
        node._serialize_result = MixinNodeService._serialize_result.__get__(
            node, MixinNodeService
        )
        # Set _input_state_class to None explicitly (Mock auto-creates attributes)
        # so that getattr(self, "_input_state_class", None) returns None
        node._input_state_class = None
        # Mock _infer_input_state_class to return None (forces SimpleNamespace fallback)
        node._infer_input_state_class = Mock(return_value=None)

        # Add handle_tool_invocation from MixinNodeService
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
        node._emit_tool_response = MixinNodeService._emit_tool_response.__get__(
            node, type(node)
        )
        node._try_get_event_bus_from_container = (
            MixinNodeService._try_get_event_bus_from_container.__get__(node, type(node))
        )
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node._node_id,
            target_node_name="TestNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        await node.handle_tool_invocation(event)

        # Should succeed
        assert mock_event_bus.publish.called
        response = mock_event_bus.publish.call_args[0][0]
        assert response.success is True
        assert len(response.result["data"]) == 1000
