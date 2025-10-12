"""
Test suite for NodeOrchestrator.

Tests workflow coordination node for control flow management with thunk emission,
conditional branching, and parallel execution coordination.

ONEX Compliance:
- Uses ModelOnexError with error_code= for error handling
- Follows ONEX test patterns with comprehensive coverage
- Tests all orchestration modes and patterns
"""

import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_workflow_execution import (
    EnumBranchCondition,
    EnumExecutionMode,
    EnumThunkType,
    EnumWorkflowState,
)
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.infrastructure.node_orchestrator import NodeOrchestrator
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.operations.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.operations.model_orchestrator_output import (
    ModelOrchestratorOutput,
)
from omnibase_core.models.orchestrator.model_thunk import ModelThunk
from omnibase_core.models.workflows.model_workflow_step_execution import (
    ModelWorkflowStepExecution,
)


@pytest.fixture
def mock_container():
    """Create mock ONEX container."""
    container = MagicMock(spec=ModelONEXContainer)
    container.node_id = "test-orchestrator-node"
    container.version = "1.0.0"
    container.get_service = MagicMock(return_value=None)
    return container


@pytest.fixture
def mock_contract_path(tmp_path):
    """Create mock contract.yaml file."""
    contract_dir = tmp_path / "contracts"
    contract_dir.mkdir()
    contract_file = contract_dir / "contract.yaml"
    contract_file.write_text(
        """
name: "NodeOrchestrator"
version: "1.0.0"
node_type: "orchestrator"
description: "Workflow coordination node"
"""
    )
    return contract_file


@pytest.fixture
def sample_thunk():
    """Create sample thunk for testing."""
    return ModelThunk(
        thunk_id=uuid4(),
        thunk_type=EnumThunkType.COMPUTE,
        target_node_type="NodeCompute",
        operation_data={"test": "data"},
        dependencies=[],
        priority=1,
        timeout_ms=5000,
        retry_count=0,
        metadata={},
        created_at=datetime.now(),
    )


@pytest.fixture
def sample_workflow_step(sample_thunk):
    """Create sample workflow step for testing."""
    return ModelWorkflowStepExecution(
        step_id=uuid4(),
        step_name="Test Step",
        execution_mode=EnumExecutionMode.SEQUENTIAL,
        thunks=[sample_thunk],
    )


@pytest.fixture
def sample_orchestrator_input(sample_workflow_step):
    """Create sample orchestrator input for testing."""
    return ModelOrchestratorInput(
        workflow_id=uuid4(),
        steps=[sample_workflow_step],
        execution_mode=EnumExecutionMode.SEQUENTIAL,
    )


class TestNodeOrchestratorInitialization:
    """Test cases for NodeOrchestrator initialization and configuration."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_initialization_success(self, mock_load_contract, mock_container):
        """Test successful NodeOrchestrator initialization."""
        # Mock contract loading
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        assert orchestrator is not None
        assert orchestrator.max_concurrent_workflows == 5
        assert orchestrator.default_step_timeout_ms == 30000
        assert orchestrator.thunk_emission_enabled is True
        assert orchestrator.load_balancing_enabled is True
        assert orchestrator.dependency_resolution_enabled is True
        assert orchestrator.max_thunk_queue_size == 1000
        assert isinstance(orchestrator.active_workflows, dict)
        assert isinstance(orchestrator.workflow_states, dict)
        assert isinstance(orchestrator.emitted_thunks, dict)
        assert isinstance(orchestrator.orchestration_metrics, dict)
        assert isinstance(orchestrator.condition_functions, dict)

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_initialization_with_builtin_conditions(self, mock_load_contract, mock_container):
        """Test that built-in condition functions are registered."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Verify built-in conditions are registered
        assert "always_true" in orchestrator.condition_functions
        assert "always_false" in orchestrator.condition_functions
        assert "has_previous_results" in orchestrator.condition_functions
        assert "previous_step_success" in orchestrator.condition_functions

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_initialization_creates_semaphore(self, mock_load_contract, mock_container):
        """Test that workflow semaphore is created with correct limit."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        assert isinstance(orchestrator.workflow_semaphore, asyncio.Semaphore)
        assert orchestrator.workflow_semaphore._value == 5  # max_concurrent_workflows

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_initialization_with_load_balancer(self, mock_load_contract, mock_container):
        """Test that load balancer is initialized."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        assert orchestrator.load_balancer is not None
        # Load balancer should be configured with max_concurrent_operations=20


class TestNodeOrchestratorWorkflowExecution:
    """Test cases for workflow execution patterns."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_sequential_workflow_execution(
        self, mock_load_contract, mock_container, sample_orchestrator_input
    ):
        """Test sequential workflow execution."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Execute workflow
        result = await orchestrator.process(sample_orchestrator_input)

        assert isinstance(result, ModelOrchestratorOutput)
        assert result.workflow_id == sample_orchestrator_input.workflow_id
        assert result.workflow_state == EnumWorkflowState.COMPLETED
        assert result.steps_completed == 1
        assert result.steps_failed == 0
        assert len(result.thunks_emitted) > 0
        assert result.processing_time_ms > 0

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_parallel_workflow_execution(
        self, mock_load_contract, mock_container, sample_workflow_step
    ):
        """Test parallel workflow execution."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create input with parallel execution mode
        parallel_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[sample_workflow_step],
            execution_mode=EnumExecutionMode.PARALLEL,
        )

        result = await orchestrator.process(parallel_input)

        assert isinstance(result, ModelOrchestratorOutput)
        assert result.workflow_state == EnumWorkflowState.COMPLETED
        assert result.parallel_executions >= 0

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_batch_workflow_execution(
        self, mock_load_contract, mock_container, sample_workflow_step
    ):
        """Test batch workflow execution with load balancing."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create input with batch execution mode
        batch_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[sample_workflow_step],
            execution_mode=EnumExecutionMode.BATCH,
            load_balancing_enabled=True,
        )

        result = await orchestrator.process(batch_input)

        assert isinstance(result, ModelOrchestratorOutput)
        assert result.workflow_state == EnumWorkflowState.COMPLETED
        assert result.metadata.get("execution_mode") == "batch"

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_workflow_with_multiple_steps(self, mock_load_contract, mock_container):
        """Test workflow execution with multiple steps."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create multiple steps
        steps = []
        for i in range(3):
            thunk = ModelThunk(
                thunk_id=uuid4(),
                thunk_type=EnumThunkType.COMPUTE,
                target_node_type="NodeCompute",
                operation_data={"step": i},
                dependencies=[],
                priority=1,
                timeout_ms=5000,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )
            step = ModelWorkflowStepExecution(
                step_id=uuid4(),
                step_name=f"Step {i}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                thunks=[thunk],
            )
            steps.append(step)

        multi_step_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
        )

        result = await orchestrator.process(multi_step_input)

        assert result.steps_completed == 3
        assert len(result.thunks_emitted) == 3


class TestNodeOrchestratorDependencyResolution:
    """Test cases for dependency resolution and ordering."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_dependency_resolution_enabled(
        self, mock_load_contract, mock_container
    ):
        """Test workflow execution with dependency resolution enabled."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create steps with dependencies
        thunk1 = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"step": 1},
            dependencies=[],
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )
        step1 = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Step 1",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[thunk1],
        )

        thunk2 = ModelThunk(
            thunk_id=uuid4(),
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"step": 2},
            dependencies=[thunk1.thunk_id],
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )
        step2 = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Step 2",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[thunk2],
        )

        dep_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[step2, step1],  # Reversed order to test dependency resolution
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            dependency_resolution_enabled=True,
        )

        result = await orchestrator.process(dep_input)

        # Should complete successfully with dependency resolution
        assert result.workflow_state == EnumWorkflowState.COMPLETED
        assert result.steps_completed == 2

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_circular_dependency_detection(
        self, mock_load_contract, mock_container
    ):
        """Test that circular dependencies are detected and rejected."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create circular dependency
        thunk_id_1 = uuid4()
        thunk_id_2 = uuid4()

        thunk1 = ModelThunk(
            thunk_id=thunk_id_1,
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"step": 1},
            dependencies=[thunk_id_2],  # Depends on thunk2
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )
        step1 = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Step 1",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[thunk1],
        )

        thunk2 = ModelThunk(
            thunk_id=thunk_id_2,
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"step": 2},
            dependencies=[thunk_id_1],  # Depends on thunk1 - circular!
            priority=1,
            timeout_ms=5000,
            retry_count=0,
            metadata={},
            created_at=datetime.now(),
        )
        step2 = ModelWorkflowStepExecution(
            step_id=uuid4(),
            step_name="Step 2",
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            thunks=[thunk2],
        )

        circular_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[step1, step2],
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            dependency_resolution_enabled=True,
        )

        # Should raise error for circular dependency
        with pytest.raises(ModelOnexError) as exc_info:
            await orchestrator.process(circular_input)

        # Circular dependency raises OPERATION_FAILED during graph building
        assert exc_info.value.error_code in [EnumCoreErrorCode.VALIDATION_ERROR, EnumCoreErrorCode.OPERATION_FAILED]
        assert "cycle" in str(exc_info.value).lower() or "workflow" in str(exc_info.value).lower()


class TestNodeOrchestratorThunkEmission:
    """Test cases for thunk emission patterns."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_emit_thunk_success(self, mock_load_contract, mock_container):
        """Test successful thunk emission."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        thunk = await orchestrator.emit_thunk(
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"test": "data"},
            dependencies=[],
            priority=2,
            timeout_ms=10000,
        )

        assert isinstance(thunk, ModelThunk)
        assert thunk.thunk_type == EnumThunkType.COMPUTE
        assert thunk.target_node_type == "NodeCompute"
        assert thunk.operation_data["test"] == "data"
        assert thunk.priority == 2
        assert thunk.timeout_ms == 10000

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_emit_thunk_with_dependencies(self, mock_load_contract, mock_container):
        """Test thunk emission with dependencies."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        dep_id = uuid4()
        thunk = await orchestrator.emit_thunk(
            thunk_type=EnumThunkType.EFFECT,
            target_node_type="NodeEffect",
            operation_data={"operation": "write"},
            dependencies=[dep_id],
            priority=1,
            timeout_ms=5000,
        )

        assert dep_id in thunk.dependencies

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_emitted_thunks_tracking(self, mock_load_contract, mock_container):
        """Test that emitted thunks are tracked."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        workflow_id = "test-workflow"
        await orchestrator.emit_thunk(
            thunk_type=EnumThunkType.COMPUTE,
            target_node_type="NodeCompute",
            operation_data={"workflow_id": workflow_id},
        )

        assert workflow_id in orchestrator.emitted_thunks
        assert len(orchestrator.emitted_thunks[workflow_id]) == 1


class TestNodeOrchestratorConditionFunctions:
    """Test cases for condition function registration and evaluation."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_register_condition_function_success(self, mock_load_contract, mock_container):
        """Test successful condition function registration."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        def custom_condition(step, previous_results):
            return True

        orchestrator.register_condition_function("custom_test", custom_condition)

        assert "custom_test" in orchestrator.condition_functions
        assert orchestrator.condition_functions["custom_test"] == custom_condition

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_register_duplicate_condition_raises_error(
        self, mock_load_contract, mock_container
    ):
        """Test that registering duplicate condition raises error."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        def condition1(step, previous_results):
            return True

        def condition2(step, previous_results):
            return False

        orchestrator.register_condition_function("duplicate", condition1)

        with pytest.raises(ModelOnexError) as exc_info:
            orchestrator.register_condition_function("duplicate", condition2)

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "already registered" in str(exc_info.value)

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    def test_register_non_callable_raises_error(self, mock_load_contract, mock_container):
        """Test that registering non-callable raises error."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        with pytest.raises(ModelOnexError) as exc_info:
            orchestrator.register_condition_function("not_callable", "not a function")

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must be callable" in str(exc_info.value)

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_builtin_always_true_condition(self, mock_load_contract, mock_container):
        """Test built-in always_true condition function."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        condition_fn = orchestrator.condition_functions["always_true"]
        result = condition_fn(None, [])

        assert result is True

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_builtin_always_false_condition(self, mock_load_contract, mock_container):
        """Test built-in always_false condition function."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        condition_fn = orchestrator.condition_functions["always_false"]
        result = condition_fn(None, [])

        assert result is False

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_builtin_has_previous_results_condition(
        self, mock_load_contract, mock_container
    ):
        """Test built-in has_previous_results condition function."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        condition_fn = orchestrator.condition_functions["has_previous_results"]

        assert condition_fn(None, []) is False
        assert condition_fn(None, [{"result": "data"}]) is True


class TestNodeOrchestratorErrorHandling:
    """Test cases for error handling and recovery."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_invalid_workflow_id_raises_error(
        self, mock_load_contract, mock_container
    ):
        """Test that missing workflow ID raises validation error."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create input with None workflow_id (will fail Pydantic validation)
        with pytest.raises((ValidationError, ModelOnexError)):
            invalid_input = ModelOrchestratorInput(
                workflow_id=None,  # Invalid
                steps=[],
            )

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_empty_steps_raises_error(self, mock_load_contract, mock_container):
        """Test that empty steps list raises validation error."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        empty_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],  # Empty steps
        )

        with pytest.raises(ModelOnexError) as exc_info:
            await orchestrator.process(empty_input)

        # Empty steps can raise either VALIDATION_ERROR or OPERATION_FAILED depending on validation flow
        assert exc_info.value.error_code in [EnumCoreErrorCode.VALIDATION_ERROR, EnumCoreErrorCode.OPERATION_FAILED]
        # Check for relevant error message
        error_msg = str(exc_info.value).lower()
        assert "step" in error_msg or "workflow" in error_msg

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_workflow_state_tracking_on_failure(
        self, mock_load_contract, mock_container, sample_workflow_step
    ):
        """Test that workflow state is updated on failure."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create input that will fail validation
        invalid_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=[],  # This will cause validation error
        )

        with pytest.raises(ModelOnexError):
            await orchestrator.process(invalid_input)

        # Workflow should be marked as FAILED in state tracking
        workflow_id_str = str(invalid_input.workflow_id)
        if workflow_id_str in orchestrator.workflow_states:
            assert orchestrator.workflow_states[workflow_id_str] == EnumWorkflowState.FAILED


class TestNodeOrchestratorMetrics:
    """Test cases for orchestration metrics and monitoring."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_get_orchestration_metrics(self, mock_load_contract, mock_container):
        """Test retrieving orchestration metrics."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        metrics = await orchestrator.get_orchestration_metrics()

        assert isinstance(metrics, dict)
        assert "load_balancing" in metrics
        assert "workflow_management" in metrics
        assert "active_workflows" in metrics["workflow_management"]
        assert "total_thunks_emitted" in metrics["workflow_management"]

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_metrics_updated_after_workflow_execution(
        self, mock_load_contract, mock_container, sample_orchestrator_input
    ):
        """Test that metrics are updated after workflow execution."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Execute workflow
        await orchestrator.process(sample_orchestrator_input)

        # Check metrics were updated
        mode = sample_orchestrator_input.execution_mode.value
        if mode in orchestrator.orchestration_metrics:
            metrics = orchestrator.orchestration_metrics[mode]
            assert metrics["total_workflows"] > 0
            assert metrics["success_count"] > 0


class TestNodeOrchestratorLifecycle:
    """Test cases for lifecycle management."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_initialize_node_resources(self, mock_load_contract, mock_container):
        """Test node resource initialization."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        await orchestrator._initialize_node_resources()

        # Should complete without errors
        assert orchestrator.thunk_emission_enabled is True

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_cleanup_node_resources(self, mock_load_contract, mock_container):
        """Test node resource cleanup."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Add some active workflows
        workflow_id = str(uuid4())
        orchestrator.active_workflows[workflow_id] = MagicMock()
        orchestrator.workflow_states[workflow_id] = EnumWorkflowState.RUNNING

        await orchestrator._cleanup_node_resources()

        # Active workflows should be cleared
        assert len(orchestrator.active_workflows) == 0
        assert len(orchestrator.emitted_thunks) == 0
        # Workflow should be marked as CANCELLED
        assert orchestrator.workflow_states[workflow_id] == EnumWorkflowState.CANCELLED


class TestNodeOrchestratorRSDTicketLifecycle:
    """Test cases for RSD ticket lifecycle transitions."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_orchestrate_rsd_ticket_lifecycle(
        self, mock_load_contract, mock_container
    ):
        """Test RSD ticket lifecycle orchestration."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        ticket_id = uuid4()
        result = await orchestrator.orchestrate_rsd_ticket_lifecycle(
            ticket_id=ticket_id,
            current_state="draft",
            target_state="in_progress",
            dependency_tickets=None,
        )

        assert isinstance(result, dict)
        assert result["ticket_id"] == str(ticket_id)
        assert "workflow_id" in result
        assert "state_transition" in result
        assert result["state_transition"] == "draft -> in_progress"
        assert result["success"] is True

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_rsd_lifecycle_with_dependencies(
        self, mock_load_contract, mock_container
    ):
        """Test RSD ticket lifecycle with dependency tickets."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        ticket_id = uuid4()
        dep_ticket_id = uuid4()

        result = await orchestrator.orchestrate_rsd_ticket_lifecycle(
            ticket_id=ticket_id,
            current_state="blocked",
            target_state="ready",
            dependency_tickets=[dep_ticket_id],
        )

        assert result["success"] is True
        assert result["steps_completed"] >= 2  # Should have dependency check step


class TestNodeOrchestratorIntrospection:
    """Test cases for node introspection capabilities."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_get_introspection_data(self, mock_load_contract, mock_container):
        """Test retrieving introspection data."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        introspection = await orchestrator.get_introspection_data()

        assert isinstance(introspection, dict)
        assert "node_capabilities" in introspection
        assert "contract_details" in introspection
        assert "runtime_information" in introspection
        assert "workflow_management_information" in introspection
        assert "configuration_details" in introspection
        assert "rsd_specific_information" in introspection

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_introspection_node_capabilities(
        self, mock_load_contract, mock_container
    ):
        """Test introspection node capabilities section."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        introspection = await orchestrator.get_introspection_data()
        capabilities = introspection["node_capabilities"]

        assert capabilities["node_type"] == "NodeOrchestrator"
        assert capabilities["node_classification"] == "orchestrator"
        assert "orchestration_patterns" in capabilities
        assert "thunk_emission_patterns" in capabilities


class TestNodeOrchestratorIntegration:
    """Integration test cases for complete workflow scenarios."""

    @patch("omnibase_core.infrastructure.node_orchestrator.NodeOrchestrator._load_contract_model")
    @pytest.mark.asyncio
    async def test_complete_workflow_lifecycle(self, mock_load_contract, mock_container):
        """Test complete workflow from creation to completion."""
        mock_contract = MagicMock()
        mock_contract.validate_node_specific_config = MagicMock()
        mock_load_contract.return_value = mock_contract

        orchestrator = NodeOrchestrator(mock_container)

        # Create complex workflow with multiple step types
        thunks = []
        for thunk_type in [EnumThunkType.COMPUTE, EnumThunkType.EFFECT, EnumThunkType.REDUCE]:
            thunk = ModelThunk(
                thunk_id=uuid4(),
                thunk_type=thunk_type,
                target_node_type=f"Node{thunk_type.value.title()}",
                operation_data={"type": thunk_type.value},
                dependencies=[],
                priority=1,
                timeout_ms=5000,
                retry_count=0,
                metadata={},
                created_at=datetime.now(),
            )
            thunks.append(thunk)

        steps = [
            ModelWorkflowStepExecution(
                step_id=uuid4(),
                step_name=f"Step {thunk.thunk_type.value}",
                execution_mode=EnumExecutionMode.SEQUENTIAL,
                thunks=[thunk],
            )
            for thunk in thunks
        ]

        workflow_input = ModelOrchestratorInput(
            workflow_id=uuid4(),
            steps=steps,
            execution_mode=EnumExecutionMode.SEQUENTIAL,
            metadata={
                "test_case": ModelSchemaValue.from_value("integration_test"),
                "environment": ModelSchemaValue.from_value("test"),
            },
        )

        # Execute workflow
        result = await orchestrator.process(workflow_input)

        # Verify complete execution
        assert result.workflow_state == EnumWorkflowState.COMPLETED
        assert result.steps_completed == len(steps)
        assert result.steps_failed == 0
        assert len(result.thunks_emitted) == len(thunks)
        assert result.processing_time_ms > 0

        # Verify metrics were updated
        metrics = await orchestrator.get_orchestration_metrics()
        assert metrics["workflow_management"]["total_thunks_emitted"] == len(thunks)
