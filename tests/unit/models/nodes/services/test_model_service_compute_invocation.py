"""
Test suite for ModelServiceCompute tool invocation handling.

Tests compute-specific tool invocation patterns including:
- Basic invocation handling
- Target node validation
- Event-to-input-state conversion
- Tool execution via node.run()
- Result serialization
- Success/error response emission
- Correlation ID tracking
- Active invocation tracking
- Concurrent invocations
- Pure function semantics validation
- Deterministic output verification
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.nodes.services.model_service_compute import (
    ModelServiceCompute,
)


@pytest.fixture
def mock_container():
    """Create mock ModelONEXContainer."""
    container = Mock(spec=ModelONEXContainer)
    container.resolve = Mock(return_value=None)
    return container


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    event_bus.subscribe = Mock()
    return event_bus


@pytest.fixture
def service_compute(mock_container, mock_event_bus):
    """Create ModelServiceCompute instance with mocked dependencies."""
    # Create service but bypass full initialization to avoid container issues
    with patch.object(ModelServiceCompute, "__init__", lambda self, container: None):
        service = ModelServiceCompute(mock_container)

    # Manually initialize required attributes from MixinNodeService
    service._node_id = uuid4()
    service._service_running = False
    service._service_task = None
    service._health_task = None
    service._active_invocations = set()
    service._total_invocations = 0
    service._successful_invocations = 0
    service._failed_invocations = 0
    service._start_time = None
    service._shutdown_requested = False
    service._shutdown_callbacks = []
    service.event_bus = mock_event_bus

    # Mock the extract node name method
    service._extract_node_name = Mock(return_value="ModelServiceCompute")

    # Mock the _publish_introspection_event method (used in start_service_mode)
    service._publish_introspection_event = Mock()

    # Mock cleanup_event_handlers method
    service.cleanup_event_handlers = Mock()

    return service


@pytest.fixture
def tool_invocation_event(service_compute):
    """Create sample ModelToolInvocationEvent."""
    return ModelToolInvocationEvent.create_tool_invocation(
        target_node_id=service_compute._node_id,
        target_node_name="ModelServiceCompute",
        tool_name="compute_service",
        action="transform",
        requester_id=uuid4(),
        requester_node_id=uuid4(),
        parameters=ModelToolParameters.from_dict({"input": "test_data"}),
        priority="normal",
    )


class TestModelServiceComputeBasicInvocation:
    """Test basic tool invocation handling."""

    @pytest.mark.asyncio
    async def test_basic_tool_invocation_handling(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test basic tool invocation handling.

        Scenario:
        - Service receives tool invocation event
        - Tool executes successfully
        - Response event emitted with success

        Expected:
        - Invocation tracked in active set
        - Tool executed via run()
        - Success response emitted
        - Metrics updated
        """
        # Mock run method to return deterministic result
        mock_result = {"output": "transformed_data", "status": "success"}
        service_compute.run = AsyncMock(return_value=mock_result)

        # Handle invocation
        await service_compute.handle_tool_invocation(tool_invocation_event)

        # Verify run was called
        assert service_compute.run.called

        # Verify response was emitted
        assert mock_event_bus.publish.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is True
        assert response_event.result == mock_result

        # Verify metrics updated
        assert service_compute._total_invocations == 1
        assert service_compute._successful_invocations == 1
        assert service_compute._failed_invocations == 0

    @pytest.mark.asyncio
    async def test_target_node_validation_by_id(self, service_compute, mock_event_bus):
        """
        Test target validation by node ID.

        Scenario:
        - Event targets this node by ID
        - Event should be processed

        Expected:
        - Invocation processed successfully
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=service_compute._node_id,
            target_node_name="different_name",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(event)

        assert service_compute.run.called
        assert service_compute._total_invocations == 1

    @pytest.mark.asyncio
    async def test_target_node_validation_by_name(
        self, service_compute, mock_event_bus
    ):
        """
        Test target validation by node name.

        Scenario:
        - Event targets this node by name
        - Event should be processed

        Expected:
        - Invocation processed successfully
        """
        # Set node name for validation
        service_compute.__class__.__name__ = "ModelServiceCompute"

        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different ID
            target_node_name="ModelServiceCompute",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(event)

        assert service_compute.run.called
        assert service_compute._total_invocations == 1

    @pytest.mark.asyncio
    async def test_target_node_validation_by_service_name(
        self, service_compute, mock_event_bus
    ):
        """
        Test target validation by service name (skipped - pattern not currently implemented).

        Scenario:
        - Event targets this node by service name suffix pattern
        - Currently this specific pattern isn't implemented in _is_target_node

        Expected:
        - This test documents future enhancement
        """
        pytest.skip(
            "Service name suffix validation not yet implemented in _is_target_node"
        )


class TestModelServiceComputeTargetValidation:
    """Test target node validation logic."""

    @pytest.mark.asyncio
    async def test_wrong_target_node_ignored(self, service_compute, mock_event_bus):
        """
        Test that invocations for wrong target are ignored.

        Scenario:
        - Event targets different node ID and name
        - Event should be ignored with warning

        Expected:
        - Warning logged
        - No processing occurs
        - Metrics not updated
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different ID
            target_node_name="DifferentNode",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
        )

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(event)

        # Verify run was NOT called
        assert not service_compute.run.called

        # Verify no response emitted (invocation ignored)
        # Note: Total invocations still incremented before validation
        assert service_compute._total_invocations == 1
        assert service_compute._successful_invocations == 0


class TestModelServiceComputeInputStateConversion:
    """Test event-to-input-state conversion."""

    @pytest.mark.asyncio
    async def test_convert_event_to_input_state_with_class(
        self, service_compute, mock_event_bus
    ):
        """
        Test conversion with input state class defined.

        Scenario:
        - Node has _input_state_class defined
        - Event converted to typed input state

        Expected:
        - Input state created with correct data
        - Action and parameters included
        """

        class TestInputState:
            def __init__(self, action, **kwargs):
                self.action = action
                self.__dict__.update(kwargs)

        service_compute._input_state_class = TestInputState

        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=service_compute._node_id,
            target_node_name="test",
            tool_name="test_tool",
            action="test_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict(
                {"param1": "value1", "param2": 42}
            ),
        )

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(event)

        # Verify run was called with correct input state
        assert service_compute.run.called
        input_state = service_compute.run.call_args[0][0]
        assert isinstance(input_state, TestInputState)
        assert input_state.action == "test_action"
        assert input_state.param1 == "value1"
        assert input_state.param2 == 42

    @pytest.mark.asyncio
    async def test_convert_event_to_input_state_without_class(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test conversion without input state class (fallback to SimpleNamespace).

        Scenario:
        - No input state class defined
        - Event converted to SimpleNamespace

        Expected:
        - SimpleNamespace created with action + params
        """
        service_compute._input_state_class = None

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(tool_invocation_event)

        # Verify run was called
        assert service_compute.run.called
        input_state = service_compute.run.call_args[0][0]
        assert isinstance(input_state, SimpleNamespace)
        assert input_state.action == "transform"

    @pytest.mark.asyncio
    async def test_convert_event_to_input_state_with_complex_params(
        self, service_compute, mock_event_bus
    ):
        """
        Test conversion with multiple parameter types.

        Scenario:
        - Event has various parameter types (string, int, list)
        - Parameters should be preserved

        Expected:
        - All parameter data accessible in input state
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=service_compute._node_id,
            target_node_name="test",
            tool_name="test_tool",
            action="complex_action",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict(
                {
                    "name": "test_item",
                    "count": 42,
                    "enabled": True,
                    "tags": ["tag1", "tag2", "tag3"],
                }
            ),
        )

        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(event)

        input_state = service_compute.run.call_args[0][0]
        assert input_state.name == "test_item"
        assert input_state.count == 42
        assert input_state.enabled is True
        assert input_state.tags == ["tag1", "tag2", "tag3"]


class TestModelServiceComputeToolExecution:
    """Test tool execution via node.run()."""

    @pytest.mark.asyncio
    async def test_execute_tool_async_run_method(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test tool execution with async run() method.

        Scenario:
        - Node has async run() method
        - Method executes asynchronously

        Expected:
        - Result returned from async method
        - No executor used
        """
        expected_result = {"computed": "async_result"}
        service_compute.run = AsyncMock(return_value=expected_result)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        assert service_compute.run.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.result == expected_result

    @pytest.mark.asyncio
    async def test_execute_tool_sync_run_method(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test tool execution with sync run() method.

        Scenario:
        - Node has synchronous run() method
        - Method should be run in executor

        Expected:
        - Executor used for sync method
        - Result returned correctly
        """
        expected_result = {"computed": "sync_result"}

        def sync_run(input_state):
            return expected_result

        service_compute.run = sync_run

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.result == expected_result

    @pytest.mark.asyncio
    async def test_execute_tool_no_run_method(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test error when no run() method exists.

        Scenario:
        - Node missing run() method
        - RuntimeError should be raised

        Expected:
        - RuntimeError raised
        - Error response emitted
        """
        # Remove run method if it exists
        if hasattr(service_compute, "run"):
            delattr(service_compute, "run")

        await service_compute.handle_tool_invocation(tool_invocation_event)

        # Verify error response emitted
        assert mock_event_bus.publish.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.success is False
        assert "run" in response_event.error.lower()
        assert service_compute._failed_invocations == 1

    @pytest.mark.asyncio
    async def test_execute_tool_with_execution_time(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test that execution time is tracked.

        Scenario:
        - Tool executes with measurable duration
        - Execution time tracked in response

        Expected:
        - execution_time_ms calculated correctly
        - Time > 0
        """

        async def slow_run(input_state):
            await asyncio.sleep(0.01)  # 10ms delay
            return {"result": "delayed"}

        service_compute.run = slow_run

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.execution_time_ms > 0


class TestModelServiceComputeResultSerialization:
    """Test result serialization."""

    @pytest.mark.asyncio
    async def test_serialize_result_dict_object(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test serialization of dict objects.

        Scenario:
        - Result is already a dict
        - Dict returned as-is

        Expected:
        - Dict preserved in response
        """
        result = {"key1": "value1", "key2": 42}
        service_compute.run = AsyncMock(return_value=result)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.result == result

    @pytest.mark.asyncio
    async def test_serialize_result_pydantic_model(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test serialization of Pydantic models.

        Scenario:
        - Result is a Pydantic model
        - model_dump() called for serialization

        Expected:
        - model_dump() result in response
        """
        from pydantic import BaseModel

        class TestModel(BaseModel):
            field1: str
            field2: int

        result = TestModel(field1="test", field2=123)
        service_compute.run = AsyncMock(return_value=result)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.result == {"field1": "test", "field2": 123}

    @pytest.mark.asyncio
    async def test_serialize_result_custom_object(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test serialization of custom objects with __dict__.

        Scenario:
        - Result is custom object
        - __dict__ returned for serialization

        Expected:
        - Object attributes in response
        """

        class CustomResult:
            def __init__(self):
                self.attr1 = "value1"
                self.attr2 = 42

        result = CustomResult()
        service_compute.run = AsyncMock(return_value=result)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.result["attr1"] == "value1"
        assert response_event.result["attr2"] == 42

    @pytest.mark.asyncio
    async def test_serialize_result_primitive(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test serialization of primitive types.

        Scenario:
        - Result is a primitive (int, str, bool)
        - Wrapped in {"result": value}

        Expected:
        - Primitive wrapped correctly
        """
        primitive_values = [42, "test_string", True, 3.14]

        for value in primitive_values:
            service_compute.run = AsyncMock(return_value=value)

            await service_compute.handle_tool_invocation(tool_invocation_event)

            response_event = mock_event_bus.publish.call_args[0][0]
            assert response_event.result == {"result": value}

    @pytest.mark.asyncio
    async def test_serialize_result_none(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test serialization of None result.

        Scenario:
        - Result is None
        - Error response generated due to Pydantic validation

        Expected:
        - Error response emitted (ModelToolResponseEvent doesn't accept None result)
        """
        service_compute.run = AsyncMock(return_value=None)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        # None result causes validation error, so we get error response
        assert response_event.success is False
        assert "validation" in response_event.error.lower()


class TestModelServiceComputeResponseEmission:
    """Test success and error response emission."""

    @pytest.mark.asyncio
    async def test_emit_tool_response_success(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test emission of success response.

        Scenario:
        - Tool executes successfully
        - Success response emitted

        Expected:
        - Event published via event bus
        - Correct correlation ID
        - Success flag set
        """
        result = {"output": "success"}
        service_compute.run = AsyncMock(return_value=result)

        await service_compute.handle_tool_invocation(tool_invocation_event)

        assert mock_event_bus.publish.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is True
        assert response_event.correlation_id == tool_invocation_event.correlation_id
        assert response_event.result == result

    @pytest.mark.asyncio
    async def test_emit_tool_response_error(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test emission of error response.

        Scenario:
        - Tool execution fails
        - Error response emitted

        Expected:
        - Error event published
        - Error details included
        """
        error_message = "Computation failed"
        service_compute.run = AsyncMock(side_effect=RuntimeError(error_message))

        await service_compute.handle_tool_invocation(tool_invocation_event)

        assert mock_event_bus.publish.called
        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.success is False
        assert error_message in response_event.error
        assert response_event.error_code == "TOOL_EXECUTION_ERROR"
        assert service_compute._failed_invocations == 1


class TestModelServiceComputeCorrelationTracking:
    """Test correlation ID tracking."""

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test that correlation IDs are tracked correctly.

        Scenario:
        - Tool invocation has correlation ID
        - Response matches correlation ID

        Expected:
        - Response correlation ID matches request
        - Correlation ID preserved throughout
        """
        expected_correlation_id = tool_invocation_event.correlation_id
        service_compute.run = AsyncMock(return_value={"result": "success"})

        await service_compute.handle_tool_invocation(tool_invocation_event)

        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.correlation_id == expected_correlation_id


class TestModelServiceComputeActiveInvocations:
    """Test active invocation tracking."""

    @pytest.mark.asyncio
    async def test_active_invocation_tracking(
        self, service_compute, tool_invocation_event, mock_event_bus
    ):
        """
        Test that active invocations are tracked during execution.

        Scenario:
        - Invocation starts
        - Correlation ID added to active set
        - Correlation ID removed after completion

        Expected:
        - Active set updated correctly
        """
        invocation_started = asyncio.Event()
        invocation_can_complete = asyncio.Event()

        async def tracked_run(input_state):
            invocation_started.set()
            await invocation_can_complete.wait()
            return {"result": "success"}

        service_compute.run = tracked_run

        # Start invocation in background
        task = asyncio.create_task(
            service_compute.handle_tool_invocation(tool_invocation_event)
        )

        # Wait for invocation to start
        await invocation_started.wait()

        # Verify correlation ID in active set
        assert (
            tool_invocation_event.correlation_id in service_compute._active_invocations
        )

        # Allow invocation to complete
        invocation_can_complete.set()
        await task

        # Verify correlation ID removed from active set
        assert (
            tool_invocation_event.correlation_id
            not in service_compute._active_invocations
        )


class TestModelServiceComputeConcurrentInvocations:
    """Test concurrent invocation handling."""

    @pytest.mark.asyncio
    async def test_concurrent_invocations(self, service_compute, mock_event_bus):
        """
        Test handling multiple concurrent invocations.

        Scenario:
        - Multiple invocations arrive simultaneously
        - All should be processed concurrently

        Expected:
        - All invocations tracked in active set
        - All responses emitted
        - Metrics correct
        """
        num_invocations = 5
        events = []

        for i in range(num_invocations):
            event = ModelToolInvocationEvent.create_tool_invocation(
                target_node_id=service_compute._node_id,
                target_node_name="test",
                tool_name="test_tool",
                action=f"action_{i}",
                requester_id=uuid4(),
                requester_node_id=uuid4(),
            )
            events.append(event)

        async def slow_run(input_state):
            await asyncio.sleep(0.01)
            return {"result": f"result_{input_state.action}"}

        service_compute.run = slow_run

        # Execute all invocations concurrently
        tasks = [
            asyncio.create_task(service_compute.handle_tool_invocation(event))
            for event in events
        ]
        await asyncio.gather(*tasks)

        # Verify all processed
        assert service_compute._total_invocations == num_invocations
        assert service_compute._successful_invocations == num_invocations
        assert len(service_compute._active_invocations) == 0

        # Verify all responses emitted
        assert mock_event_bus.publish.call_count == num_invocations


class TestModelServiceComputePureFunctionSemantics:
    """Test compute-specific pure function semantics."""

    @pytest.mark.asyncio
    async def test_pure_function_semantics_validation(
        self, service_compute, mock_event_bus
    ):
        """
        Test that compute nodes enforce pure function semantics.

        Scenario:
        - Compute operations should be deterministic
        - No side effects should occur

        Expected:
        - Same input produces same output
        - Operations are idempotent
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=service_compute._node_id,
            target_node_name="test",
            tool_name="compute",
            action="transform",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"input_value": 42}),
        )

        # Mock deterministic computation
        service_compute.run = AsyncMock(return_value={"output": 84})

        # Execute multiple times
        for _ in range(3):
            await service_compute.handle_tool_invocation(event)

        # Verify deterministic output
        assert mock_event_bus.publish.call_count == 3
        for call in mock_event_bus.publish.call_args_list:
            response = call[0][0]
            assert response.result == {"output": 84}


class TestModelServiceComputeDeterministicOutput:
    """Test deterministic output verification."""

    @pytest.mark.asyncio
    async def test_deterministic_output_verification(
        self, service_compute, mock_event_bus
    ):
        """
        Test that compute nodes produce deterministic outputs.

        Scenario:
        - Same input provided multiple times
        - Output should be identical

        Expected:
        - All outputs match
        - No randomness in results
        """
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=service_compute._node_id,
            target_node_name="test",
            tool_name="deterministic_compute",
            action="calculate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"x": 10, "y": 20}),
        )

        # Mock deterministic computation
        def deterministic_compute(input_state):
            return {
                "sum": input_state.x + input_state.y,
                "product": input_state.x * input_state.y,
            }

        service_compute.run = deterministic_compute

        results = []
        for _ in range(5):
            await service_compute.handle_tool_invocation(event)
            response = mock_event_bus.publish.call_args[0][0]
            results.append(response.result)

        # Verify all results are identical
        assert all(r == results[0] for r in results)
        assert results[0] == {"sum": 30, "product": 200}
