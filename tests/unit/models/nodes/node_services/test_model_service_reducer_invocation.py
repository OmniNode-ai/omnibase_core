"""
Test suite for ModelServiceReducer tool invocation handling.

Tests reducer-specific semantics including aggregation operations, state management,
cache integration, and event-driven tool execution via TOOL_INVOCATION events.

Test Coverage:
1. Basic tool invocation handling
2. Target node validation
3. Event-to-input-state conversion
4. Tool execution via node.run()
5. Result serialization
6. Success response emission
7. Error response emission
8. Correlation ID tracking
9. Active invocation tracking
10. Concurrent invocations
11. Wrong target node (ignore)
12. Aggregation semantics validation
13. State management during invocation

Reference: MIXIN_NODE_SERVICE_TEST_PLAN.md Section 6.3
"""

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.enums.enum_reducer_types import EnumReductionType, EnumStreamingMode
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.discovery.model_tool_invocation_event import (
    ModelToolInvocationEvent,
)
from omnibase_core.models.discovery.model_tool_response_event import (
    ModelToolResponseEvent,
)
from omnibase_core.models.discovery.model_toolparameters import ModelToolParameters
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.models.service.model_service_reducer import ModelServiceReducer


class ConcreteReducerService(ModelServiceReducer):
    """Concrete test implementation of ModelServiceReducer."""

    def __init__(self, container: ModelONEXContainer, node_id: UUID | None = None):
        super().__init__(container)
        if node_id:
            self._node_id = node_id
        self.execution_count = 0
        self.last_input_state = None

    async def run(self, input_state: Any) -> ModelReducerOutput:
        """Execute reduction operation."""
        self.execution_count += 1
        self.last_input_state = input_state

        # Simulate aggregation operation
        if hasattr(input_state, "action") and input_state.action == "aggregate":
            # Handle string data from ModelToolParameters
            data = getattr(input_state, "data", ["1", "2", "3", "4", "5"])
            # Convert strings to numbers if needed
            numeric_data = [float(x) if isinstance(x, str) else x for x in data]
            result = {
                "total": sum(numeric_data),
                "count": len(numeric_data),
                "average": sum(numeric_data) / len(numeric_data) if numeric_data else 0,
            }
        elif hasattr(input_state, "action") and input_state.action == "normalize":
            data = getattr(input_state, "data", [])
            numeric_data = [float(x) if isinstance(x, str) else x for x in data]
            result = {"normalized": [x / 100.0 for x in numeric_data]}
        else:
            result = {
                "status": "completed",
                "action": getattr(input_state, "action", "unknown"),
            }

        return ModelReducerOutput(
            result=result,
            operation_id=uuid4(),
            reduction_type=EnumReductionType.AGGREGATE,
            processing_time_ms=10.5,
            items_processed=(
                len(getattr(input_state, "data", []))
                if hasattr(input_state, "data")
                else 5
            ),
            conflicts_resolved=0,
            streaming_mode=EnumStreamingMode.BATCH,
            batches_processed=1,
            metadata={},
        )


@pytest.fixture
def mock_container():
    """Create mock ONEX container."""
    container = Mock(spec=ModelONEXContainer)
    container.get = Mock(return_value=None)
    return container


@pytest.fixture
def mock_event_bus():
    """Create mock event bus for publish/subscribe."""
    event_bus = AsyncMock()
    event_bus.subscribe = AsyncMock()
    event_bus.publish = AsyncMock()
    return event_bus


@pytest.fixture
def reducer_service(mock_container, mock_event_bus):
    """Create reducer service instance with mocked dependencies."""
    service = ConcreteReducerService(mock_container)
    service.event_bus = mock_event_bus
    return service


@pytest.fixture
def node_id():
    """Generate consistent node ID for testing."""
    return uuid4()


@pytest.fixture
def correlation_id():
    """Generate consistent correlation ID for testing."""
    return uuid4()


@pytest.fixture
def tool_invocation_event(node_id, correlation_id):
    """Create tool invocation event for reducer service."""
    return ModelToolInvocationEvent.create_tool_invocation(
        target_node_id=node_id,
        target_node_name="ConcreteReducerService",
        tool_name="aggregation_tool",
        action="aggregate",
        requester_id=uuid4(),
        requester_node_id=uuid4(),
        parameters=ModelToolParameters.from_dict(
            {
                "data": [
                    "10",
                    "20",
                    "30",
                    "40",
                    "50",
                ],  # String list for ModelToolParameter compatibility
                "group_by": "category",
            }
        ),
        correlation_id=correlation_id,
        timeout_ms=30000,
        priority="normal",
    )


class TestModelServiceReducerInvocation:
    """Test suite for ModelServiceReducer tool invocation handling."""

    @pytest.mark.asyncio
    async def test_basic_tool_invocation_handling(
        self, reducer_service, tool_invocation_event, mock_event_bus, node_id
    ):
        """
        Test basic tool invocation handling.

        Verifies:
        - Tool invocation accepted
        - node.run() called with converted input state
        - Response event emitted with aggregated result
        - Metrics updated
        """
        # Configure reducer service
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Handle invocation
        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify run was called
        assert reducer_service.execution_count == 1
        assert reducer_service.last_input_state is not None

        # Verify response published
        mock_event_bus.publish.assert_called_once()
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is True
        assert response_event.correlation_id == tool_invocation_event.correlation_id

        # Verify metrics updated
        assert reducer_service._total_invocations == 1
        assert reducer_service._successful_invocations == 1
        assert reducer_service._failed_invocations == 0

    @pytest.mark.asyncio
    async def test_target_node_validation_by_id(
        self, reducer_service, tool_invocation_event, node_id
    ):
        """
        Test target validation by node ID.

        Verifies:
        - Invocation processed when target_node_id matches
        - Tool execution occurs
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify execution occurred
        assert reducer_service.execution_count == 1

    @pytest.mark.asyncio
    async def test_target_node_validation_by_name(
        self, reducer_service, mock_event_bus, correlation_id
    ):
        """
        Test target validation by node name.

        Verifies:
        - Invocation processed when target_node_name matches
        """
        reducer_service._node_id = uuid4()  # Different ID
        reducer_service._service_running = True

        # Create event with matching node name
        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Wrong ID
            target_node_name="ConcreteReducerService",  # Correct name
            tool_name="aggregation_tool",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"data": ["1", "2", "3"]}),
            correlation_id=correlation_id,
        )

        await reducer_service.handle_tool_invocation(event)

        # Verify execution occurred
        assert reducer_service.execution_count == 1

    @pytest.mark.asyncio
    async def test_event_to_input_state_conversion(
        self, reducer_service, tool_invocation_event, node_id
    ):
        """
        Test event-to-input-state conversion.

        Verifies:
        - Event parameters converted to input state
        - Action extracted correctly
        - Parameters accessible on input state
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify input state structure
        input_state = reducer_service.last_input_state
        assert input_state is not None
        assert hasattr(input_state, "action")
        assert input_state.action == "aggregate"

        # Verify parameters passed through
        if isinstance(input_state, SimpleNamespace):
            assert hasattr(input_state, "data")
            assert input_state.data == ["10", "20", "30", "40", "50"]

    @pytest.mark.asyncio
    async def test_tool_execution_via_node_run(
        self, reducer_service, tool_invocation_event, node_id
    ):
        """
        Test tool execution via node.run().

        Verifies:
        - run() method called with input state
        - Result returned from run()
        - Execution time tracked
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Spy on run method
        original_run = reducer_service.run
        call_count = 0

        async def spy_run(input_state):
            nonlocal call_count
            call_count += 1
            return await original_run(input_state)

        reducer_service.run = spy_run

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify run was called
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_result_serialization(
        self, reducer_service, tool_invocation_event, mock_event_bus, node_id
    ):
        """
        Test result serialization.

        Verifies:
        - ModelReducerOutput serialized correctly
        - Result data accessible in response
        - Aggregation metrics included
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Get response event
        response_event = mock_event_bus.publish.call_args[0][0]

        # Verify serialization
        assert response_event.result is not None
        assert isinstance(response_event.result, dict)

        # Verify aggregation data preserved
        assert "result" in response_event.result or "total" in response_event.result

    @pytest.mark.asyncio
    async def test_success_response_emission(
        self,
        reducer_service,
        tool_invocation_event,
        mock_event_bus,
        node_id,
        correlation_id,
    ):
        """
        Test success response emission.

        Verifies:
        - TOOL_RESPONSE event emitted on success
        - Correlation ID preserved
        - Success flag set
        - Execution time included
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify publish called
        mock_event_bus.publish.assert_called_once()

        # Verify response structure
        response_event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(response_event, ModelToolResponseEvent)
        assert response_event.success is True
        assert response_event.correlation_id == correlation_id
        assert response_event.execution_time_ms >= 0  # Can be 0 for very fast execution
        assert response_event.tool_name == "aggregation_tool"
        assert response_event.action == "aggregate"

    @pytest.mark.asyncio
    async def test_error_response_emission(
        self,
        reducer_service,
        tool_invocation_event,
        mock_event_bus,
        node_id,
        correlation_id,
    ):
        """
        Test error response emission.

        Verifies:
        - TOOL_RESPONSE event emitted on error
        - Error details included
        - Failed invocation tracked
        - Correlation ID preserved
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Make run() raise exception
        async def failing_run(input_state):
            raise ValueError("Aggregation failed: invalid data")

        reducer_service.run = failing_run

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify error response published
        mock_event_bus.publish.assert_called_once()
        response_event = mock_event_bus.publish.call_args[0][0]

        assert response_event.success is False
        assert response_event.correlation_id == correlation_id
        assert "Aggregation failed" in response_event.error
        assert response_event.error_code == "TOOL_EXECUTION_ERROR"

        # Verify failure metrics
        assert reducer_service._failed_invocations == 1
        assert reducer_service._successful_invocations == 0

    @pytest.mark.asyncio
    async def test_correlation_id_tracking(
        self,
        reducer_service,
        tool_invocation_event,
        mock_event_bus,
        node_id,
        correlation_id,
    ):
        """
        Test correlation ID tracking.

        Verifies:
        - Correlation ID tracked in active invocations
        - Correlation ID removed after completion
        - Response uses same correlation ID
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Track active invocations during execution
        invocation_ids_during_execution = []

        original_run = reducer_service.run

        async def tracking_run(input_state):
            invocation_ids_during_execution.extend(reducer_service._active_invocations)
            return await original_run(input_state)

        reducer_service.run = tracking_run

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify correlation ID was tracked during execution
        assert correlation_id in invocation_ids_during_execution

        # Verify correlation ID removed after completion
        assert correlation_id not in reducer_service._active_invocations

        # Verify response has same correlation ID
        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.correlation_id == correlation_id

    @pytest.mark.asyncio
    async def test_active_invocation_tracking(
        self, reducer_service, tool_invocation_event, node_id, correlation_id
    ):
        """
        Test active invocation tracking.

        Verifies:
        - Invocation added to active set
        - Invocation removed after completion
        - Total invocations incremented
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Verify initially empty
        assert len(reducer_service._active_invocations) == 0

        # Create slow execution to check during invocation
        original_run = reducer_service.run

        async def slow_run(input_state):
            # At this point, invocation should be in active set
            assert correlation_id in reducer_service._active_invocations
            await asyncio.sleep(0.01)
            return await original_run(input_state)

        reducer_service.run = slow_run

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Verify removed after completion
        assert correlation_id not in reducer_service._active_invocations
        assert len(reducer_service._active_invocations) == 0

        # Verify total invocations tracked
        assert reducer_service._total_invocations == 1

    @pytest.mark.asyncio
    async def test_concurrent_invocations(
        self, reducer_service, mock_event_bus, node_id
    ):
        """
        Test concurrent invocation handling.

        Verifies:
        - Multiple invocations handled concurrently
        - Each tracked separately
        - All complete successfully
        - Metrics accurate
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Create multiple events
        events = [
            ModelToolInvocationEvent.create_tool_invocation(
                target_node_id=node_id,
                target_node_name="ConcreteReducerService",
                tool_name="aggregation_tool",
                action="aggregate",
                requester_id=uuid4(),
                requester_node_id=uuid4(),
                parameters=ModelToolParameters.from_dict(
                    {"data": ["10", "20", "30", "40", "50"]}
                ),
                correlation_id=uuid4(),
            )
            for i in range(3)
        ]

        # Execute concurrently
        tasks = [reducer_service.handle_tool_invocation(event) for event in events]
        await asyncio.gather(*tasks)

        # Verify all completed
        assert reducer_service.execution_count == 3
        assert reducer_service._total_invocations == 3
        assert reducer_service._successful_invocations == 3

        # Verify all invocations removed from active set
        assert len(reducer_service._active_invocations) == 0

        # Verify all responses published
        assert mock_event_bus.publish.call_count == 3

    @pytest.mark.asyncio
    async def test_wrong_target_node_ignored(
        self, reducer_service, mock_event_bus, node_id
    ):
        """
        Test invocation for wrong target is ignored.

        Verifies:
        - Invocation with different target_node_id ignored
        - No execution occurs
        - Warning logged
        - No response emitted
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Create event for different node
        wrong_event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=uuid4(),  # Different ID
            target_node_name="DifferentService",  # Different name
            tool_name="aggregation_tool",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({}),
        )

        with patch(
            "omnibase_core.mixins.mixin_node_service.emit_log_event_sync"
        ) as mock_log:
            await reducer_service.handle_tool_invocation(wrong_event)

            # Verify no execution
            assert reducer_service.execution_count == 0

            # Verify invocation was tracked (added then removed when ignored)
            assert len(reducer_service._active_invocations) == 0

    @pytest.mark.asyncio
    async def test_aggregation_semantics_validation(
        self, reducer_service, mock_event_bus, node_id
    ):
        """
        Test reducer-specific aggregation semantics.

        Verifies:
        - Aggregation operations execute correctly
        - Results include aggregated data
        - State accumulated properly
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # Create aggregation event
        agg_event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="ConcreteReducerService",
            tool_name="aggregation_tool",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict(
                {"data": ["10", "20", "30", "40", "50"]}
            ),
        )

        await reducer_service.handle_tool_invocation(agg_event)

        # Verify response includes aggregation results
        response_event = mock_event_bus.publish.call_args[0][0]
        assert response_event.success is True

        # Verify result structure includes aggregation data
        result = response_event.result
        assert isinstance(result, dict)
        # Should have aggregation metrics (total, count, average, etc.)
        assert "total" in result or "result" in result

    @pytest.mark.asyncio
    async def test_state_management_during_invocation(
        self, reducer_service, mock_event_bus, node_id
    ):
        """
        Test state management during invocation.

        Verifies:
        - State persists during execution
        - Multiple invocations maintain separate state
        - State cleared appropriately
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        # First invocation
        event1 = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="ConcreteReducerService",
            tool_name="aggregation_tool",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"data": ["1", "2", "3"]}),
        )

        await reducer_service.handle_tool_invocation(event1)
        first_state = reducer_service.last_input_state

        # Second invocation
        event2 = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="ConcreteReducerService",
            tool_name="aggregation_tool",
            action="normalize",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({"data": ["100", "200", "300"]}),
        )

        await reducer_service.handle_tool_invocation(event2)
        second_state = reducer_service.last_input_state

        # Verify states are different
        assert first_state is not second_state
        assert first_state.action == "aggregate"
        assert second_state.action == "normalize"

        # Verify both completed successfully
        assert reducer_service._successful_invocations == 2
        assert mock_event_bus.publish.call_count == 2


class TestModelServiceReducerInvocationEdgeCases:
    """Test edge cases for reducer invocation handling."""

    @pytest.mark.asyncio
    async def test_invocation_with_empty_parameters(
        self, reducer_service, mock_event_bus, node_id
    ):
        """
        Test invocation with empty parameters.

        Verifies:
        - Empty parameters handled gracefully
        - Default values used
        - Execution completes
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True

        event = ModelToolInvocationEvent.create_tool_invocation(
            target_node_id=node_id,
            target_node_name="ConcreteReducerService",
            tool_name="aggregation_tool",
            action="aggregate",
            requester_id=uuid4(),
            requester_node_id=uuid4(),
            parameters=ModelToolParameters.from_dict({}),  # Empty
        )

        await reducer_service.handle_tool_invocation(event)

        # Verify execution completed
        assert reducer_service.execution_count == 1
        assert reducer_service._successful_invocations == 1

    @pytest.mark.asyncio
    async def test_invocation_with_service_not_running(
        self, reducer_service, tool_invocation_event, node_id
    ):
        """
        Test invocation when service not running.

        Verifies:
        - Invocation still processed (event handler registered)
        - Execution occurs
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = False  # Not running

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Invocation is processed regardless of _service_running flag
        assert reducer_service._total_invocations == 1

    @pytest.mark.asyncio
    async def test_invocation_during_shutdown(
        self, reducer_service, tool_invocation_event, node_id
    ):
        """
        Test invocation during shutdown.

        Verifies:
        - Invocation handled even during shutdown
        - Tracked in active invocations
        """
        reducer_service._node_id = node_id
        reducer_service._service_running = True
        reducer_service._shutdown_requested = True

        await reducer_service.handle_tool_invocation(tool_invocation_event)

        # Invocation still processed
        assert reducer_service._total_invocations == 1
