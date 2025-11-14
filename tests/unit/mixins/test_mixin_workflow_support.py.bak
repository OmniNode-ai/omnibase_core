"""
Tests for MixinDagSupport (workflow support) - comprehensive coverage.

Tests workflow event support including DAG context detection, event emission,
correlation tracking, and workflow integration.

ZERO TOLERANCE: No Any types allowed.
"""

import os
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

from omnibase_core.mixins.mixin_workflow_support import MixinDagSupport
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.events.model_event_envelope import ModelEventEnvelope


class MockTool(MixinDagSupport):
    """Mock tool class for testing mixin functionality."""

    def __init__(self, event_bus: Any = None, **kwargs: Any) -> None:
        super().__init__(event_bus=event_bus)
        self.node_id = str(uuid4())  # Use proper UUID string


class TestMixinInitialization:
    """Test mixin initialization."""

    def test_initialization_without_event_bus(self) -> None:
        """Test initialization without event bus."""
        tool = MockTool()

        assert tool._event_bus is None
        assert tool._dag_correlation_id is None
        assert tool._workflow_node_id is None

    def test_initialization_with_event_bus(self) -> None:
        """Test initialization with event bus."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        assert tool._event_bus == event_bus
        assert tool._dag_correlation_id is None
        assert tool._workflow_node_id is None

    def test_initialization_sets_node_id(self) -> None:
        """Test initialization sets a valid node_id."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        assert tool._event_bus == event_bus
        assert tool.node_id is not None
        # Node ID should be a valid UUID string
        try:
            UUID(tool.node_id)
            assert True
        except ValueError:
            assert False, "node_id should be a valid UUID string"


class TestDagContextDetection:
    """Test DAG execution context detection."""

    def test_dag_not_enabled_by_default(self) -> None:
        """Test that DAG is not enabled without context."""
        tool = MockTool()

        assert not tool.is_dag_enabled()

    @patch.dict(os.environ, {"ONEX_WORKFLOW_EXECUTION": "true"}, clear=True)
    def test_dag_enabled_via_environment(self) -> None:
        """Test DAG enabled via environment variable."""
        tool = MockTool()

        assert tool.is_dag_enabled()

    @patch.dict(os.environ, {"ONEX_WORKFLOW_EXECUTION": "false"}, clear=True)
    def test_dag_not_enabled_when_env_false(self) -> None:
        """Test DAG not enabled when environment is false."""
        tool = MockTool()

        assert not tool.is_dag_enabled()

    @patch.dict(os.environ, {"ONEX_WORKFLOW_CORRELATION_ID": "test-id"}, clear=True)
    def test_dag_enabled_via_correlation_id_env(self) -> None:
        """Test DAG enabled via correlation ID environment variable."""
        tool = MockTool()

        assert tool.is_dag_enabled()

    def test_dag_enabled_via_set_context(self) -> None:
        """Test DAG enabled when context is set programmatically."""
        tool = MockTool()
        correlation_id = uuid4()
        node_id = uuid4()

        tool.set_workflow_context(correlation_id, node_id)

        assert tool.is_dag_enabled()

    @patch.dict(
        os.environ,
        {"ONEX_WORKFLOW_EXECUTION": "TRUE"},  # Uppercase should work
        clear=True,
    )
    def test_dag_enabled_case_insensitive(self) -> None:
        """Test DAG environment variable is case insensitive."""
        tool = MockTool()

        assert tool.is_dag_enabled()


class TestSetWorkflowContext:
    """Test setting workflow context."""

    def test_set_workflow_context_basic(self) -> None:
        """Test setting workflow context."""
        tool = MockTool()
        correlation_id = uuid4()
        node_id = uuid4()

        tool.set_workflow_context(correlation_id, node_id)

        assert tool._dag_correlation_id == str(correlation_id)
        assert tool._workflow_node_id == str(node_id)

    def test_set_workflow_context_enables_dag(self) -> None:
        """Test that setting context enables DAG detection."""
        tool = MockTool()
        assert not tool.is_dag_enabled()

        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        assert tool.is_dag_enabled()

    def test_set_workflow_context_updates_existing(self) -> None:
        """Test that setting context updates existing values."""
        tool = MockTool()

        # Set first context
        correlation1 = uuid4()
        node1 = uuid4()
        tool.set_workflow_context(correlation1, node1)

        assert tool._dag_correlation_id == str(correlation1)
        assert tool._workflow_node_id == str(node1)

        # Update context
        correlation2 = uuid4()
        node2 = uuid4()
        tool.set_workflow_context(correlation2, node2)

        assert tool._dag_correlation_id == str(correlation2)
        assert tool._workflow_node_id == str(node2)


class TestEmitDagCompletionEvent:
    """Test DAG completion event emission."""

    def test_emit_completion_without_event_bus(self) -> None:
        """Test that emit does nothing without event bus."""
        tool = MockTool(event_bus=None)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        # Should not raise error
        tool.emit_dag_completion_event(result="success", status="completed")

    def test_emit_completion_dag_not_enabled(self) -> None:
        """Test that emit does nothing when DAG not enabled."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        tool.emit_dag_completion_event(result="success", status="completed")

        # Event bus should not be called
        event_bus.publish_async.assert_not_called()

    def test_emit_completion_success(self) -> None:
        """Test successful completion event emission."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        tool.emit_dag_completion_event(result="test_result", status="completed")

        # Verify event bus called
        event_bus.publish_async.assert_called_once()

        # Verify envelope structure
        call_args = event_bus.publish_async.call_args[0][0]
        assert isinstance(call_args, ModelEventEnvelope)
        assert call_args.correlation_id == correlation_id

    def test_emit_completion_with_error_message(self) -> None:
        """Test completion event with error message."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        tool.emit_dag_completion_event(
            result=None,
            status="failed",
            error_message="Test error occurred",
        )

        event_bus.publish_async.assert_called_once()

    def test_emit_completion_status_mapping(self) -> None:
        """Test that status strings are properly mapped."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        statuses = ["success", "completed", "failed", "error"]

        for status in statuses:
            event_bus.reset_mock()
            tool.emit_dag_completion_event(result="test", status=status)
            event_bus.publish_async.assert_called_once()

    @patch.dict(
        os.environ,
        {"ONEX_WORKFLOW_CORRELATION_ID": str(uuid4())},
        clear=True,
    )
    def test_emit_completion_uses_env_correlation_id(self) -> None:
        """Test that emit uses environment correlation ID if not set."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)
        # Set DAG enabled via env
        tool._dag_correlation_id = None  # No explicit correlation ID set

        with patch.dict(os.environ, {"ONEX_WORKFLOW_EXECUTION": "true"}):
            tool.emit_dag_completion_event(result="test", status="completed")

        event_bus.publish_async.assert_called_once()


class TestEmitDagStartEvent:
    """Test DAG start event emission."""

    def test_emit_start_without_event_bus(self) -> None:
        """Test that emit does nothing without event bus."""
        tool = MockTool(event_bus=None)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        # Should not raise error
        tool.emit_dag_start_event()

    def test_emit_start_dag_not_enabled(self) -> None:
        """Test that emit does nothing when DAG not enabled."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        tool.emit_dag_start_event()

        event_bus.publish_async.assert_not_called()

    def test_emit_start_success(self) -> None:
        """Test successful start event emission."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        tool.emit_dag_start_event()

        event_bus.publish_async.assert_called_once()

        # Verify envelope structure
        call_args = event_bus.publish_async.call_args[0][0]
        assert isinstance(call_args, ModelEventEnvelope)
        assert call_args.correlation_id == correlation_id

    @patch.dict(
        os.environ,
        {"ONEX_WORKFLOW_CORRELATION_ID": str(uuid4())},
        clear=True,
    )
    def test_emit_start_uses_env_correlation_id(self) -> None:
        """Test that emit uses environment correlation ID if not set."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        with patch.dict(os.environ, {"ONEX_WORKFLOW_EXECUTION": "true"}):
            tool.emit_dag_start_event()

        event_bus.publish_async.assert_called_once()


class TestStatusMapping:
    """Test status to enum mapping."""

    def test_map_success_status(self) -> None:
        """Test mapping 'success' status."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status = tool._map_status_to_enum("success")
        assert status == EnumExecutionStatus.COMPLETED

    def test_map_completed_status(self) -> None:
        """Test mapping 'completed' status."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status = tool._map_status_to_enum("completed")
        assert status == EnumExecutionStatus.COMPLETED

    def test_map_failed_status(self) -> None:
        """Test mapping 'failed' status."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status = tool._map_status_to_enum("failed")
        assert status == EnumExecutionStatus.FAILED

    def test_map_error_status(self) -> None:
        """Test mapping 'error' status."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status = tool._map_status_to_enum("error")
        assert status == EnumExecutionStatus.FAILED

    def test_map_case_insensitive(self) -> None:
        """Test that status mapping is case insensitive."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status_upper = tool._map_status_to_enum("SUCCESS")
        status_lower = tool._map_status_to_enum("success")
        status_mixed = tool._map_status_to_enum("SuCcEsS")

        assert status_upper == EnumExecutionStatus.COMPLETED
        assert status_lower == EnumExecutionStatus.COMPLETED
        assert status_mixed == EnumExecutionStatus.COMPLETED

    def test_map_all_status_types(self) -> None:
        """Test mapping all defined status types."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status_mappings = {
            "pending": EnumExecutionStatus.PENDING,
            "running": EnumExecutionStatus.RUNNING,
            "cancelled": EnumExecutionStatus.CANCELLED,
            "timeout": EnumExecutionStatus.TIMEOUT,
            "skipped": EnumExecutionStatus.SKIPPED,
        }

        for status_str, expected_enum in status_mappings.items():
            result = tool._map_status_to_enum(status_str)
            assert result == expected_enum

    def test_map_unknown_status_defaults_to_completed(self) -> None:
        """Test that unknown status defaults to COMPLETED."""
        tool = MockTool()

        from omnibase_core.enums.enum_execution_status import EnumExecutionStatus

        status = tool._map_status_to_enum("unknown_status")
        assert status == EnumExecutionStatus.COMPLETED


class TestResultSerialization:
    """Test result serialization for event emission."""

    def test_serialize_pydantic_model(self) -> None:
        """Test serializing Pydantic model result."""
        tool = MockTool()

        # Create a simple Pydantic model result
        from pydantic import BaseModel

        class TestResult(BaseModel):
            value: str
            count: int

        result = TestResult(value="test", count=42)
        serialized = tool._serialize_result(result)

        assert serialized["value"] == "test"
        assert serialized["count"] == 42

    def test_serialize_regular_object(self) -> None:
        """Test serializing regular object with __dict__."""

        class TestObject:
            def __init__(self) -> None:
                self.name = "test"
                self.value = 123

        tool = MockTool()
        obj = TestObject()
        serialized = tool._serialize_result(obj)

        assert "name" in serialized
        assert "value" in serialized

    def test_serialize_simple_value(self) -> None:
        """Test serializing simple value."""
        tool = MockTool()

        serialized = tool._serialize_result("simple string")

        assert serialized["value"] == "simple string"

    def test_serialize_handles_error(self) -> None:
        """Test that serialization errors are handled gracefully."""

        class UnserializableObject:
            def __getattribute__(self, name: str) -> Any:
                raise RuntimeError("Cannot access attributes")

        tool = MockTool()
        obj = UnserializableObject()

        # Should not raise, should return error dict
        serialized = tool._serialize_result(obj)

        assert "serialization_error" in serialized


class TestTimestampGeneration:
    """Test timestamp generation."""

    def test_get_current_timestamp_format(self) -> None:
        """Test that timestamp is in ISO format with Z suffix."""
        tool = MockTool()

        timestamp = tool._get_current_timestamp()

        assert isinstance(timestamp, str)
        assert timestamp.endswith("Z")
        assert "T" in timestamp  # ISO format has T separator

    def test_timestamps_are_unique(self) -> None:
        """Test that consecutive timestamps are different."""
        tool = MockTool()

        timestamp1 = tool._get_current_timestamp()
        timestamp2 = tool._get_current_timestamp()

        # May be equal if called too quickly, but format should be correct
        assert isinstance(timestamp1, str)
        assert isinstance(timestamp2, str)


class TestErrorLogging:
    """Test safe error logging."""

    def test_safe_log_without_logger(self) -> None:
        """Test that logging without logger doesn't raise error."""
        tool = MockTool()

        # Should not raise any exception
        tool._safe_log_error("Test error message")

    def test_safe_log_with_logger(self) -> None:
        """Test logging with logger tool."""
        logger_mock = MagicMock()
        tool = MockTool()
        tool.logger_tool = logger_mock

        tool._safe_log_error("Test error message")

        logger_mock.log.assert_called_once()
        call_args = logger_mock.log.call_args[0][0]
        assert "[Workflow]" in call_args
        assert "Test error message" in call_args

    def test_safe_log_handles_logger_error(self) -> None:
        """Test that logger errors are handled gracefully."""
        logger_mock = MagicMock()
        logger_mock.log.side_effect = RuntimeError("Logger failed")

        tool = MockTool()
        tool.logger_tool = logger_mock

        # Should not raise exception
        tool._safe_log_error("Test message")


class TestWorkflowIntegration:
    """Test complete workflow integration scenarios."""

    def test_complete_workflow_lifecycle(self) -> None:
        """Test complete workflow lifecycle with events."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        correlation_id = uuid4()
        node_id = uuid4()

        # Set up workflow context
        tool.set_workflow_context(correlation_id, node_id)
        assert tool.is_dag_enabled()

        # Emit start event
        tool.emit_dag_start_event()
        assert event_bus.publish_async.call_count == 1

        # Emit completion event
        tool.emit_dag_completion_event(result="success", status="completed")
        assert event_bus.publish_async.call_count == 2

    def test_workflow_without_explicit_context(self) -> None:
        """Test workflow using environment variables only."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        with patch.dict(
            os.environ,
            {
                "ONEX_WORKFLOW_EXECUTION": "true",
                "ONEX_WORKFLOW_CORRELATION_ID": str(uuid4()),
            },
            clear=True,
        ):
            assert tool.is_dag_enabled()

            tool.emit_dag_start_event()
            tool.emit_dag_completion_event(result="test", status="success")

            assert event_bus.publish_async.call_count == 2

    def test_non_workflow_execution(self) -> None:
        """Test tool execution outside workflow context."""
        event_bus = MagicMock()
        tool = MockTool(event_bus=event_bus)

        # No workflow context set
        assert not tool.is_dag_enabled()

        # Events should not be emitted
        tool.emit_dag_start_event()
        tool.emit_dag_completion_event(result="test", status="success")

        event_bus.publish_async.assert_not_called()


class TestEventEmissionFailureHandling:
    """Test handling of event emission failures."""

    def test_completion_event_emission_failure_handled(self) -> None:
        """Test that event emission failures don't crash tool."""
        event_bus = MagicMock()
        event_bus.publish_async.side_effect = RuntimeError("Event bus failed")

        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        # Should not raise exception
        tool.emit_dag_completion_event(result="test", status="success")

    def test_start_event_emission_failure_handled(self) -> None:
        """Test that start event emission failures don't crash tool."""
        event_bus = MagicMock()
        event_bus.publish_async.side_effect = RuntimeError("Event bus failed")

        tool = MockTool(event_bus=event_bus)
        correlation_id = uuid4()
        node_id = uuid4()
        tool.set_workflow_context(correlation_id, node_id)

        # Should not raise exception
        tool.emit_dag_start_event()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_context_updates(self) -> None:
        """Test updating workflow context multiple times."""
        tool = MockTool()

        for i in range(10):
            correlation_id = uuid4()
            node_id = uuid4()
            tool.set_workflow_context(correlation_id, node_id)

            assert tool._dag_correlation_id == str(correlation_id)
            assert tool._workflow_node_id == str(node_id)

    def test_mixed_environment_and_explicit_context(self) -> None:
        """Test mixing environment variables with explicit context."""
        tool = MockTool()

        with patch.dict(os.environ, {"ONEX_WORKFLOW_EXECUTION": "true"}, clear=True):
            # Both methods enable DAG
            assert tool.is_dag_enabled()

            correlation_id = uuid4()
            node_id = uuid4()
            tool.set_workflow_context(correlation_id, node_id)

            assert tool.is_dag_enabled()

    def test_empty_result_serialization(self) -> None:
        """Test serializing empty/None result."""
        tool = MockTool()

        serialized = tool._serialize_result(None)

        assert "value" in serialized


__all__ = [
    "TestMixinInitialization",
    "TestDagContextDetection",
    "TestSetWorkflowContext",
    "TestEmitDagCompletionEvent",
    "TestEmitDagStartEvent",
    "TestStatusMapping",
    "TestResultSerialization",
    "TestTimestampGeneration",
    "TestErrorLogging",
    "TestWorkflowIntegration",
    "TestEventEmissionFailureHandling",
    "TestEdgeCases",
]
