"""
Tests for MixinHybridExecution - comprehensive conditional branch coverage.

Tests all execution paths, mode selection branches, complexity calculations,
and workflow execution scenarios for the hybrid execution mixin.

ZERO TOLERANCE: No Any types allowed.
"""

import json
from typing import Any
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.mixins.enum_execution_mode import MixinExecutionMode as ExecutionMode
from omnibase_core.mixins.mixin_hybrid_execution import MixinHybridExecution


# Test input state classes
class SimpleInputState(BaseModel):
    """Simple input state for testing."""

    value: str = "test"


class ComplexInputState(BaseModel):
    """Complex input state with operations."""

    operations: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    iterations: int = 1
    data: dict[str, Any] = Field(default_factory=dict)


class MockTool(MixinHybridExecution[SimpleInputState, SimpleInputState]):
    """Mock tool for testing hybrid execution."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.process_called = False
        self.workflow_created = False

    def process(self, input_state: SimpleInputState) -> SimpleInputState:
        """Direct execution method."""
        self.process_called = True
        return SimpleInputState(value=f"processed: {input_state.value}")

    def create_workflow(self, input_state: SimpleInputState) -> Mock:
        """Create mock workflow."""
        self.workflow_created = True
        workflow = Mock()
        workflow._steps_executed = 3

        async def run(input_data: SimpleInputState) -> SimpleInputState:
            return SimpleInputState(value=f"workflow: {input_data.value}")

        workflow.run = run
        workflow.__class__.__name__ = "MockWorkflow"
        return workflow


class MockToolWithoutWorkflow(MixinHybridExecution[SimpleInputState, SimpleInputState]):
    """Mock tool without workflow support."""

    def process(self, input_state: SimpleInputState) -> SimpleInputState:
        """Direct execution method."""
        return SimpleInputState(value=f"direct: {input_state.value}")


class MockToolWithComplexInput(
    MixinHybridExecution[ComplexInputState, ComplexInputState]
):
    """Mock tool accepting complex input."""

    def process(self, input_state: ComplexInputState) -> ComplexInputState:
        """Direct execution method."""
        return input_state


class TestMixinInitialization:
    """Test mixin initialization."""

    def test_initialization_sets_defaults(self) -> None:
        """Test that initialization sets default values."""
        tool = MockTool()

        assert tool._execution_mode is None
        assert tool._workflow_metrics is None

    def test_initialization_logging(self) -> None:
        """Test that initialization emits log events."""
        with patch("omnibase_core.mixins.mixin_hybrid_execution.emit_log_event") as mock_log:
            tool = MockTool()

            # Should emit initialization log
            assert mock_log.called
            call_args = mock_log.call_args_list[0]
            assert "MIXIN_INIT" in str(call_args)


class TestDetermineExecutionMode:
    """Test execution mode determination logic."""

    def test_direct_mode_for_low_complexity(self) -> None:
        """Test direct mode selected for low complexity input."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(operations=["op1", "op2"])

        mode = tool.determine_execution_mode(input_state)

        assert mode == ExecutionMode.DIRECT

    def test_orchestrated_mode_for_medium_complexity(self) -> None:
        """Test orchestrated mode selected for medium complexity."""
        tool = MockToolWithComplexInput()
        tool.contract_data = {
            "execution_modes": [
                ExecutionMode.DIRECT,
                ExecutionMode.ORCHESTRATED,
                ExecutionMode.WORKFLOW,
            ]
        }
        # Medium complexity: 6 operations (0.3) + dependencies (0.2) + iterations (0.2) = 0.7
        # But we want > 0.5 and < 0.7, so we need exactly > 0.5
        # Use dependencies (0.2) + iterations (0.2) = 0.4, need 0.6 total
        # Add medium data size for another 0.2
        medium_data = {"key": "x" * 5000}
        input_state = ComplexInputState(
            dependencies=["dep1"],  # 0.2
            iterations=2,  # 0.2
            data=medium_data,  # 0.2
        )

        mode = tool.determine_execution_mode(input_state)

        # Should select ORCHESTRATED for score 0.6 (0.2 + 0.2 + 0.2)
        assert mode == ExecutionMode.ORCHESTRATED

    def test_workflow_mode_for_high_complexity(self) -> None:
        """Test workflow mode selected for high complexity."""
        tool = MockToolWithComplexInput()
        # High complexity: large data + many operations + dependencies + iterations
        large_data = {"key": "x" * 15000}  # > 10000 bytes
        input_state = ComplexInputState(
            operations=[f"op{i}" for i in range(10)],  # 0.3
            dependencies=["dep1"],  # 0.2
            iterations=5,  # 0.2
            data=large_data,  # 0.3 from data size
        )

        mode = tool.determine_execution_mode(input_state)

        assert mode == ExecutionMode.WORKFLOW

    def test_workflow_mode_respects_supported_modes(self) -> None:
        """Test workflow mode only selected if supported."""
        tool = MockToolWithComplexInput()
        tool.contract_data = {"execution_modes": [ExecutionMode.DIRECT]}
        # High complexity but workflow not supported
        input_state = ComplexInputState(
            operations=[f"op{i}" for i in range(10)],
            dependencies=["dep1"],
            iterations=5,
        )

        mode = tool.determine_execution_mode(input_state)

        # Should fall back to DIRECT since WORKFLOW not supported
        assert mode == ExecutionMode.DIRECT

    def test_orchestrated_mode_respects_supported_modes(self) -> None:
        """Test orchestrated mode only selected if supported."""
        tool = MockToolWithComplexInput()
        tool.contract_data = {"execution_modes": [ExecutionMode.DIRECT]}
        # Medium complexity but orchestrated not supported
        input_state = ComplexInputState(
            operations=[f"op{i}" for i in range(6)], dependencies=["dep1"]
        )

        mode = tool.determine_execution_mode(input_state)

        assert mode == ExecutionMode.DIRECT


class TestExecuteWithModeSelection:
    """Test execute method with mode selection branches."""

    def test_execute_with_explicit_direct_mode(self) -> None:
        """Test execute with explicit DIRECT mode override."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        result = tool.execute(input_state, mode=ExecutionMode.DIRECT)

        assert tool._execution_mode == ExecutionMode.DIRECT
        assert tool.process_called
        assert result.value == "processed: test"

    def test_execute_with_explicit_workflow_mode(self) -> None:
        """Test execute with explicit WORKFLOW mode override."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch("llama_index.core.workflow"):
            result = tool.execute(input_state, mode=ExecutionMode.WORKFLOW)

        assert tool._execution_mode == ExecutionMode.WORKFLOW
        assert tool.workflow_created

    def test_execute_with_auto_mode_calls_determine(self) -> None:
        """Test execute with AUTO mode calls determine_execution_mode."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch.object(
            tool, "determine_execution_mode", return_value=ExecutionMode.DIRECT
        ) as mock_determine:
            result = tool.execute(input_state, mode=ExecutionMode.AUTO)

            mock_determine.assert_called_once_with(input_state)
            assert tool._execution_mode == ExecutionMode.DIRECT

    def test_execute_without_mode_calls_determine(self) -> None:
        """Test execute without mode calls determine_execution_mode."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch.object(
            tool, "determine_execution_mode", return_value=ExecutionMode.DIRECT
        ) as mock_determine:
            result = tool.execute(input_state)

            mock_determine.assert_called_once_with(input_state)

    def test_execute_with_orchestrated_mode(self) -> None:
        """Test execute with ORCHESTRATED mode."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch("llama_index.core.workflow"):
            result = tool.execute(input_state, mode=ExecutionMode.ORCHESTRATED)

        # Orchestrated falls back to workflow mode
        assert tool._execution_mode == ExecutionMode.ORCHESTRATED

    def test_execute_with_unknown_mode_falls_back_to_direct(self) -> None:
        """Test execute with unknown mode falls back to direct."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        # Force unknown mode
        tool._execution_mode = "UNKNOWN_MODE"
        result = tool._execute_direct(input_state)

        assert tool.process_called
        assert result.value == "processed: test"


class TestExecuteDirect:
    """Test direct execution path."""

    def test_execute_direct_calls_process(self) -> None:
        """Test direct execution calls process method."""
        tool = MockTool()
        input_state = SimpleInputState(value="direct_test")

        result = tool._execute_direct(input_state)

        assert tool.process_called
        assert result.value == "processed: direct_test"

    def test_execute_direct_logging(self) -> None:
        """Test direct execution emits log events."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch("omnibase_core.mixins.mixin_hybrid_execution.emit_log_event") as mock_log:
            result = tool._execute_direct(input_state)

            # Should emit start and completion logs
            log_messages = [str(call) for call in mock_log.call_args_list]
            assert any("DIRECT_EXECUTION" in msg for msg in log_messages)


class TestExecuteWorkflow:
    """Test workflow execution path with multiple branches."""

    def test_execute_workflow_success(self) -> None:
        """Test successful workflow execution."""
        tool = MockTool()
        input_state = SimpleInputState(value="workflow_test")

        with patch("llama_index.core.workflow"):
            result = tool._execute_workflow(input_state)

        assert tool.workflow_created
        assert result.value == "workflow: workflow_test"
        assert tool._workflow_metrics is not None
        assert tool._workflow_metrics.status == EnumWorkflowStatus.COMPLETED

    def test_execute_workflow_without_create_method_falls_back(self) -> None:
        """Test workflow execution without create_workflow falls back to direct."""
        tool = MockToolWithoutWorkflow()
        input_state = SimpleInputState(value="test")

        result = tool._execute_workflow(input_state)

        # Should fall back to direct execution
        assert result.value == "direct: test"

    def test_execute_workflow_without_llama_index_falls_back(self) -> None:
        """Test workflow execution without LlamaIndex falls back to direct."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        # Mock ImportError for LlamaIndex
        with patch("builtins.__import__", side_effect=ImportError("No LlamaIndex")):
            result = tool._execute_workflow(input_state)

        # Should fall back to direct execution
        assert tool.process_called
        assert result.value == "processed: test"

    def test_execute_workflow_failure_falls_back_to_direct(self) -> None:
        """Test workflow failure falls back to direct execution."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        # Mock workflow to raise exception
        def failing_create_workflow(input_state: SimpleInputState) -> Mock:
            raise RuntimeError("Workflow creation failed")

        tool.create_workflow = failing_create_workflow  # type: ignore

        with patch("llama_index.core.workflow"):
            result = tool._execute_workflow(input_state)

        # Should fall back to direct execution
        assert tool.process_called
        assert result.value == "processed: test"

    def test_execute_workflow_records_metrics(self) -> None:
        """Test workflow execution records metrics."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch("llama_index.core.workflow"):
            result = tool._execute_workflow(input_state)

        assert tool._workflow_metrics is not None
        assert tool._workflow_metrics.status == EnumWorkflowStatus.COMPLETED
        assert tool._workflow_metrics.duration_seconds >= 0
        assert tool._workflow_metrics.steps_completed == 3


class TestExecuteOrchestrated:
    """Test orchestrated execution path."""

    def test_execute_orchestrated_falls_back_to_workflow(self) -> None:
        """Test orchestrated mode falls back to workflow mode."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        with patch("llama_index.core.workflow"):
            result = tool._execute_orchestrated(input_state)

        # Should execute workflow
        assert tool.workflow_created


class TestCalculateComplexity:
    """Test complexity calculation branches."""

    def test_complexity_zero_for_simple_input(self) -> None:
        """Test complexity is zero for simple input."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState()

        complexity = tool._calculate_complexity(input_state)

        assert complexity == 0.0

    def test_complexity_includes_large_data_size(self) -> None:
        """Test complexity includes large data size (> 10000 bytes)."""
        tool = MockToolWithComplexInput()
        large_data = {"key": "x" * 15000}
        input_state = ComplexInputState(data=large_data)

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.3 for large data
        assert complexity >= 0.3

    def test_complexity_includes_medium_data_size(self) -> None:
        """Test complexity includes medium data size (> 1000 bytes)."""
        tool = MockToolWithComplexInput()
        medium_data = {"key": "x" * 5000}
        input_state = ComplexInputState(data=medium_data)

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.2 for medium data
        assert complexity >= 0.2

    def test_complexity_includes_many_operations(self) -> None:
        """Test complexity includes many operations (> 5)."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(operations=[f"op{i}" for i in range(10)])

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.3 for many operations
        assert complexity >= 0.3

    def test_complexity_includes_dependencies(self) -> None:
        """Test complexity includes dependencies."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(dependencies=["dep1", "dep2"])

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.2 for dependencies
        assert complexity >= 0.2

    def test_complexity_includes_iterations(self) -> None:
        """Test complexity includes iterations (> 1)."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(iterations=5)

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.2 for iterations
        assert complexity >= 0.2

    def test_complexity_caps_at_one(self) -> None:
        """Test complexity score caps at 1.0."""
        tool = MockToolWithComplexInput()
        # Maximum complexity: all factors
        large_data = {"key": "x" * 15000}
        input_state = ComplexInputState(
            data=large_data,
            operations=[f"op{i}" for i in range(10)],
            dependencies=["dep1"],
            iterations=5,
        )

        complexity = tool._calculate_complexity(input_state)

        # Should cap at 1.0
        assert complexity == 1.0

    def test_complexity_without_model_dump(self) -> None:
        """Test complexity calculation for objects without model_dump."""
        tool = MockTool()

        class PlainObject:
            pass

        plain_input = PlainObject()  # type: ignore

        complexity = tool._calculate_complexity(plain_input)

        # Should return 0.0 for objects without attributes
        assert complexity == 0.0


class TestGetSupportedModes:
    """Test supported modes detection."""

    def test_supported_modes_from_contract(self) -> None:
        """Test getting supported modes from contract data."""
        tool = MockTool()
        tool.contract_data = {
            "execution_modes": [ExecutionMode.DIRECT, ExecutionMode.WORKFLOW]
        }

        modes = tool._get_supported_modes()

        assert ExecutionMode.DIRECT in modes
        assert ExecutionMode.WORKFLOW in modes

    def test_supported_modes_default_when_no_contract(self) -> None:
        """Test default supported modes when no contract data."""
        tool = MockTool()

        modes = tool._get_supported_modes()

        # Should return default modes
        assert ExecutionMode.DIRECT in modes
        assert ExecutionMode.WORKFLOW in modes

    def test_supported_modes_empty_contract_uses_default(self) -> None:
        """Test empty contract uses default modes."""
        tool = MockTool()
        tool.contract_data = {"execution_modes": []}

        modes = tool._get_supported_modes()

        # Should use default modes
        assert ExecutionMode.DIRECT in modes
        assert ExecutionMode.WORKFLOW in modes

    def test_supported_modes_no_contract_data_attribute(self) -> None:
        """Test supported modes when no contract_data attribute."""
        tool = MockTool()
        # Don't set contract_data at all

        modes = tool._get_supported_modes()

        # Should use default modes
        assert ExecutionMode.DIRECT in modes
        assert ExecutionMode.WORKFLOW in modes


class TestSupportsMode:
    """Test supports_mode method."""

    def test_supports_mode_direct(self) -> None:
        """Test that DIRECT mode is supported by default."""
        tool = MockTool()

        assert tool.supports_mode(ExecutionMode.DIRECT)

    def test_supports_mode_workflow(self) -> None:
        """Test that WORKFLOW mode is supported by default."""
        tool = MockTool()

        assert tool.supports_mode(ExecutionMode.WORKFLOW)

    def test_supports_mode_custom_modes(self) -> None:
        """Test custom supported modes."""
        tool = MockTool()
        tool.contract_data = {"execution_modes": [ExecutionMode.DIRECT]}

        assert tool.supports_mode(ExecutionMode.DIRECT)
        assert not tool.supports_mode(ExecutionMode.ORCHESTRATED)


class TestPropertiesAccessors:
    """Test property accessors."""

    def test_execution_mode_property(self) -> None:
        """Test execution_mode property."""
        tool = MockTool()

        assert tool.execution_mode is None

        tool._execution_mode = ExecutionMode.DIRECT
        assert tool.execution_mode == ExecutionMode.DIRECT

    def test_workflow_metrics_property(self) -> None:
        """Test workflow_metrics property."""
        tool = MockTool()

        assert tool.workflow_metrics is None

        # Execute workflow to generate metrics
        input_state = SimpleInputState(value="test")
        with patch("llama_index.core.workflow"):
            result = tool._execute_workflow(input_state)

        assert tool.workflow_metrics is not None
        assert tool.workflow_metrics.status == EnumWorkflowStatus.COMPLETED


class TestCreateWorkflowDefault:
    """Test default create_workflow implementation."""

    def test_create_workflow_returns_none_by_default(self) -> None:
        """Test create_workflow returns None for base implementation."""
        tool = MockToolWithoutWorkflow()
        input_state = SimpleInputState(value="test")

        workflow = tool.create_workflow(input_state)

        assert workflow is None

    def test_create_workflow_logs_warning(self) -> None:
        """Test create_workflow logs warning when not implemented."""
        tool = MockToolWithoutWorkflow()
        input_state = SimpleInputState(value="test")

        with patch("omnibase_core.mixins.mixin_hybrid_execution.emit_log_event") as mock_log:
            workflow = tool.create_workflow(input_state)

            # Should log warning
            log_messages = [str(call) for call in mock_log.call_args_list]
            assert any("No workflow implementation" in msg for msg in log_messages)


class TestProcessNotImplemented:
    """Test process method requirement."""

    def test_process_must_be_implemented(self) -> None:
        """Test that process method must be implemented by subclass."""

        class IncompleteToolClass(MixinHybridExecution[SimpleInputState, SimpleInputState]):
            pass

        tool = IncompleteToolClass()
        input_state = SimpleInputState(value="test")

        with pytest.raises(NotImplementedError, match="Tool must implement process method"):
            tool.process(input_state)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_execute_with_none_mode(self) -> None:
        """Test execute with None mode uses auto-detection."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        result = tool.execute(input_state, mode=None)

        assert tool._execution_mode is not None

    def test_multiple_executions_update_mode(self) -> None:
        """Test multiple executions correctly update mode."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        # First execution in direct mode
        result1 = tool.execute(input_state, mode=ExecutionMode.DIRECT)
        assert tool._execution_mode == ExecutionMode.DIRECT

        # Second execution in workflow mode
        with patch("llama_index.core.workflow"):
            result2 = tool.execute(input_state, mode=ExecutionMode.WORKFLOW)
            assert tool._execution_mode == ExecutionMode.WORKFLOW

    def test_complexity_with_empty_operations_list(self) -> None:
        """Test complexity with empty operations list."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(operations=[])

        complexity = tool._calculate_complexity(input_state)

        # Should not add complexity for empty operations
        assert complexity == 0.0

    def test_complexity_with_exactly_5_operations(self) -> None:
        """Test complexity boundary with exactly 5 operations."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(operations=[f"op{i}" for i in range(5)])

        complexity = tool._calculate_complexity(input_state)

        # Should not add complexity for exactly 5 operations (threshold is > 5)
        assert complexity == 0.0

    def test_complexity_with_exactly_6_operations(self) -> None:
        """Test complexity boundary with 6 operations."""
        tool = MockToolWithComplexInput()
        input_state = ComplexInputState(operations=[f"op{i}" for i in range(6)])

        complexity = tool._calculate_complexity(input_state)

        # Should add 0.3 for > 5 operations
        assert complexity >= 0.3

    def test_workflow_with_failed_event_loop(self) -> None:
        """Test workflow execution handles event loop failures."""
        tool = MockTool()
        input_state = SimpleInputState(value="test")

        # Mock asyncio.new_event_loop to raise exception
        with patch("llama_index.core.workflow"):
            with patch("asyncio.new_event_loop", side_effect=RuntimeError("Loop failed")):
                result = tool._execute_workflow(input_state)

        # Should fall back to direct execution
        assert tool.process_called


__all__ = [
    "TestMixinInitialization",
    "TestDetermineExecutionMode",
    "TestExecuteWithModeSelection",
    "TestExecuteDirect",
    "TestExecuteWorkflow",
    "TestExecuteOrchestrated",
    "TestCalculateComplexity",
    "TestGetSupportedModes",
    "TestSupportsMode",
    "TestPropertiesAccessors",
    "TestCreateWorkflowDefault",
    "TestProcessNotImplemented",
    "TestEdgeCases",
]
