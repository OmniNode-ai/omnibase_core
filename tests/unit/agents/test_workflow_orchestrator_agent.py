"""
Unit tests for WorkflowOrchestratorAgent.

Tests the workflow orchestrator agent implementation including
protocol compliance, operation routing, and execution state management.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import uuid4

import pytest

from omnibase_core.agents.models.model_orchestrator_parameters import (
    ModelOrchestratorParameters,
)
from omnibase_core.agents.workflow_orchestrator_agent import WorkflowOrchestratorAgent
from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError
from omnibase_core.enums.enum_onex_status import EnumOnexStatus
from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
from omnibase_core.protocol.models.model_workflow_input_state import (
    ModelWorkflowInputState,
)


def create_mock_onex_result(
    status=EnumOnexStatus.SUCCESS, result_data=None, error_message=None
):
    """Helper function to create mock ModelOnexResult for tests."""
    from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata

    mock_result = Mock()
    mock_result.status = status

    # Create metadata object to match new ModelGenericMetadata interface
    metadata_dict = {}
    if result_data:
        metadata_dict["result_data"] = result_data
    if error_message:
        metadata_dict["error"] = error_message

    mock_result.metadata = ModelGenericMetadata.from_dict(metadata_dict)
    return mock_result


class TestWorkflowOrchestratorAgent:
    """Test suite for WorkflowOrchestratorAgent."""

    @pytest.fixture
    def mock_container(self):
        """Create mock ONEX container."""
        container = Mock()
        container.get_service.return_value = Mock()
        return container

    @pytest.fixture
    def orchestrator_agent(self, mock_container):
        """Create WorkflowOrchestratorAgent instance."""
        with patch.object(WorkflowOrchestratorAgent, "__init__", return_value=None):
            agent = WorkflowOrchestratorAgent.__new__(WorkflowOrchestratorAgent)
            agent.container = mock_container
            agent._execution_states = {}
            agent._execution_states_lock = threading.RLock()
            agent._registry = None
            agent._registry_lock = threading.RLock()

            # Enhanced workflow coordination tracking (new attributes)
            agent._workflow_instances = {}
            agent._workflow_instances_lock = threading.RLock()
            agent._coordination_results = {}
            agent._coordination_results_lock = threading.RLock()

            # Node coordination patterns
            agent._node_coordination_config = {
                "COMPUTE": {"assignment_strategy": "load_balanced"},
                "EFFECT": {"assignment_strategy": "capability_matched"},
                "REDUCER": {"assignment_strategy": "state_affinity"},
            }

            agent._last_cleanup_time = datetime.now()
            agent._cleanup_stats = {
                "total_cleanups": 0,
                "states_removed_ttl": 0,
                "states_removed_limit": 0,
                "max_states_held": 0,
                "avg_cleanup_duration_ms": 0.0,
                "workflows_created": 0,
                "workflows_executed": 0,
                "coordination_failures": 0,
                "active_workflows": 0,
            }
            agent.node_id = "test-orchestrator-001"
            return agent

    def test_agent_initialization(self, mock_container):
        """Test agent initialization with ONEX container."""
        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with patch.object(WorkflowOrchestratorAgent.__bases__[0], "__init__"):
                agent = WorkflowOrchestratorAgent(mock_container)

                assert hasattr(agent, "_execution_states")
                assert hasattr(agent, "_registry")
                assert agent._registry is None
                assert isinstance(agent._execution_states, dict)

    def test_set_registry(self, orchestrator_agent):
        """Test setting the node registry."""
        mock_registry = Mock()

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            orchestrator_agent.set_registry(mock_registry)

        assert orchestrator_agent._registry == mock_registry

    def test_run_with_valid_input(self, orchestrator_agent):
        """Test running orchestrator with valid input state."""
        from omnibase_core.models.service.model_workflow_parameters import (
            ModelWorkflowParameters,
        )

        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id="test-scenario-123",
            operation_type="generic",
            correlation_id=str(uuid4()),
            parameters=ModelWorkflowParameters(),
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with patch.object(
                orchestrator_agent, "orchestrate_operation"
            ) as mock_orchestrate:
                mock_orchestrate.return_value = create_mock_onex_result()

                result = orchestrator_agent.run(input_state)

                assert result.status == EnumOnexStatus.SUCCESS
                mock_orchestrate.assert_called_once()

    def test_run_with_exception(self, orchestrator_agent):
        """Test running orchestrator when exception occurs."""
        from omnibase_core.models.service.model_workflow_parameters import (
            ModelWorkflowParameters,
        )

        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id="test-scenario-456",
            operation_type="generic",
            correlation_id=str(uuid4()),
            parameters=ModelWorkflowParameters(),
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with patch.object(
                orchestrator_agent, "orchestrate_operation"
            ) as mock_orchestrate:
                mock_orchestrate.side_effect = Exception("Test error")

                result = orchestrator_agent.run(input_state)

                assert result.status == EnumOnexStatus.ERROR
                assert hasattr(result.metadata, "error")

    def test_orchestrate_model_generation(self, orchestrator_agent):
        """Test orchestrating model generation operation."""
        scenario_id = "test-scenario-789"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            execution_mode="sequential",
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            # Ensure ModelOnexResult can be instantiated for this test
            from omnibase_core.models.core.model_onex_result import ModelOnexResult

            try:
                ModelOnexResult.model_rebuild()
            except Exception:
                pass  # Continue if rebuild fails

            result = orchestrator_agent.orchestrate_operation(
                operation_type="model_generation",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "model_generation"
        assert result.metadata.result_data["scenario_id"] == scenario_id
        assert result.run_id == correlation_id

        # Check execution state was created
        assert scenario_id in orchestrator_agent._execution_states
        execution_state = orchestrator_agent._execution_states[scenario_id]
        assert execution_state.scenario_id == scenario_id
        assert execution_state.status == EnumWorkflowStatus.COMPLETED

    def test_orchestrate_bootstrap_validation(self, orchestrator_agent):
        """Test orchestrating bootstrap validation operation."""
        scenario_id = "test-validation-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            execution_mode="parallel",
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            result = orchestrator_agent.orchestrate_operation(
                operation_type="bootstrap_validation",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "bootstrap_validation"
        assert result.metadata.result_data["execution_mode"] == "parallel"

    def test_orchestrate_extraction(self, orchestrator_agent):
        """Test orchestrating extraction operation."""
        scenario_id = "test-extraction-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            execution_mode="batch",
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            result = orchestrator_agent.orchestrate_operation(
                operation_type="extraction",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "extraction"

    def test_orchestrate_workflow_coordination(self, orchestrator_agent):
        """Test orchestrating workflow coordination operation."""
        scenario_id = "test-coordination-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            execution_mode="conditional",
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            result = orchestrator_agent.orchestrate_operation(
                operation_type="workflow_coordination",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "workflow_coordination"

    def test_orchestrate_dependency_resolution(self, orchestrator_agent):
        """Test orchestrating dependency resolution operation."""
        scenario_id = "test-dependency-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id,
            correlation_id=correlation_id,
            execution_mode="streaming",
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            result = orchestrator_agent.orchestrate_operation(
                operation_type="dependency_resolution",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "dependency_resolution"

    def test_orchestrate_generic_operation(self, orchestrator_agent):
        """Test orchestrating generic operation."""
        scenario_id = "test-generic-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id, correlation_id=correlation_id
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            result = orchestrator_agent.orchestrate_operation(
                operation_type="generic",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        assert result.status == EnumOnexStatus.SUCCESS
        assert result.metadata.result_data["operation"] == "generic"

    def test_orchestrate_operation_with_exception(self, orchestrator_agent):
        """Test orchestrating operation when handler raises exception."""
        scenario_id = "test-error-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id, correlation_id=correlation_id
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with patch.object(
                orchestrator_agent, "_handle_generic_operation"
            ) as mock_handler:
                mock_handler.side_effect = Exception("Handler error")

                result = orchestrator_agent.orchestrate_operation(
                    operation_type="generic",
                    scenario_id=scenario_id,
                    correlation_id=correlation_id,
                    parameters=parameters,
                )

        assert result.status == EnumOnexStatus.ERROR
        assert hasattr(result.metadata, "error")

        # Check execution state was marked as failed
        assert scenario_id in orchestrator_agent._execution_states
        execution_state = orchestrator_agent._execution_states[scenario_id]
        assert execution_state.status == EnumWorkflowStatus.FAILED

    def test_get_execution_state_existing(self, orchestrator_agent):
        """Test getting execution state for existing scenario."""
        scenario_id = "test-existing-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id, correlation_id=correlation_id
        )

        # First orchestrate to create execution state
        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            orchestrator_agent.orchestrate_operation(
                operation_type="generic",
                scenario_id=scenario_id,
                correlation_id=correlation_id,
                parameters=parameters,
            )

        # Then get execution state
        execution_state = orchestrator_agent.get_execution_state(scenario_id)

        assert execution_state is not None
        assert execution_state.execution_context.correlation_id == correlation_id
        assert execution_state.total_nodes == 1

    def test_get_execution_state_nonexistent(self, orchestrator_agent):
        """Test getting execution state for non-existent scenario."""
        execution_state = orchestrator_agent.get_execution_state("nonexistent-scenario")
        assert execution_state is None

    def test_health_check_healthy(self, orchestrator_agent):
        """Test health check when orchestrator is healthy."""
        with patch.object(
            orchestrator_agent.__class__.__bases__[0], "health_check"
        ) as mock_base_health:
            mock_base_health.return_value = Mock(is_healthy=True)

            health_result = orchestrator_agent.health_check()

        assert health_result.status == "healthy"
        assert health_result.service_name == "EnhancedWorkflowOrchestratorAgent"
        assert "workflow_orchestration" in health_result.capabilities
        assert "dependency_management" in health_result.capabilities
        assert (
            health_result.dependencies_healthy is False
        )  # Registry is None in test fixture
        assert len(health_result.errors) == 0

    def test_health_check_with_active_workflows(self, orchestrator_agent):
        """Test health check with active workflows affecting score."""
        # Create many active workflow states to test health scoring
        for i in range(150):  # Create more than threshold of 100
            scenario_id = f"active-scenario-{i}"
            from datetime import datetime

            from omnibase_core.agents.models.model_orchestrator_execution_state import (
                ModelOrchestratorExecutionState,
            )

            execution_state = ModelOrchestratorExecutionState(
                scenario_id=scenario_id,
                status=EnumWorkflowStatus.RUNNING,  # Active workflow
                start_time=datetime.now(),
                correlation_id=f"corr-{i}",
                operation_type="test",
            )
            orchestrator_agent._execution_states[scenario_id] = execution_state

        with patch.object(
            orchestrator_agent.__class__.__bases__[0], "health_check"
        ) as mock_base_health:
            mock_base_health.return_value = Mock(is_healthy=True)

            health_result = orchestrator_agent.health_check()

        assert (
            len(health_result.warnings) > 0
        )  # Should have warnings due to high workflow load
        assert "High workflow load detected" in health_result.warnings[0]

    def test_health_check_with_exception(self, orchestrator_agent):
        """Test health check when exception occurs."""
        with patch.object(
            orchestrator_agent.__class__.__bases__[0], "health_check"
        ) as mock_base_health:
            mock_base_health.side_effect = Exception("Health check error")

            with patch(
                "omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"
            ):
                health_result = orchestrator_agent.health_check()

        assert health_result.status == "unhealthy"
        assert health_result.service_name == "EnhancedWorkflowOrchestratorAgent"
        assert "Health check error" in health_result.errors

    def test_operation_routing(self, orchestrator_agent):
        """Test that operations are routed to correct handlers."""
        scenario_id = "test-routing-001"
        correlation_id = str(uuid4())
        parameters = ModelOrchestratorParameters(
            scenario_id=scenario_id, correlation_id=correlation_id
        )

        from datetime import datetime

        from omnibase_core.agents.models.model_orchestrator_execution_state import (
            ModelOrchestratorExecutionState,
        )

        execution_state = ModelOrchestratorExecutionState(
            scenario_id=scenario_id,
            status=EnumWorkflowStatus.RUNNING,
            start_time=datetime.now(),
            correlation_id=correlation_id,
            operation_type="test",
        )

        # Test each operation type routes to expected handler
        operation_handlers = {
            "model_generation": "_handle_model_generation",
            "bootstrap_validation": "_handle_bootstrap_validation",
            "extraction": "_handle_extraction",
            "workflow_coordination": "_handle_workflow_coordination",
            "dependency_resolution": "_handle_dependency_resolution",
            "unknown_operation": "_handle_generic_operation",  # Should fallback to generic
        }

        for operation_type, expected_handler in operation_handlers.items():
            with patch(
                "omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"
            ):
                with patch.object(orchestrator_agent, expected_handler) as mock_handler:
                    mock_handler.return_value = Mock(success=True)

                    orchestrator_agent._route_operation(
                        operation_type=operation_type,
                        scenario_id=scenario_id,
                        parameters=parameters,
                        execution_state=execution_state,
                    )

                    mock_handler.assert_called_once()

    def test_input_validation_security_checks(self, orchestrator_agent):
        """Test comprehensive input validation and security checks."""
        from omnibase_core.models.service.model_workflow_parameters import (
            ModelWorkflowParameters,
        )

        # Test scenario_id with dangerous characters
        dangerous_scenario_id = "test-scenario-../../etc/passwd"
        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=dangerous_scenario_id,
            operation_type="generic",
            correlation_id=str(uuid4()),
            parameters=ModelWorkflowParameters(),
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with pytest.raises(OnexError) as exc_info:
                orchestrator_agent.run(input_state)

            assert "dangerous character sequence" in str(exc_info.value)

    def test_input_validation_length_limits(self, orchestrator_agent):
        """Test input validation length limits."""
        from omnibase_core.models.service.model_workflow_parameters import (
            ModelWorkflowParameters,
        )

        # Test scenario_id length limit
        long_scenario_id = "x" * 256  # Exceeds 255 character limit
        input_state = ModelWorkflowInputState(
            action="orchestrate",
            scenario_id=long_scenario_id,
            operation_type="generic",
            correlation_id=str(uuid4()),
            parameters=ModelWorkflowParameters(),
        )

        with patch("omnibase_core.agents.workflow_orchestrator_agent.emit_log_event"):
            with pytest.raises(OnexError) as exc_info:
                orchestrator_agent.run(input_state)

            assert "exceeds maximum length" in str(exc_info.value)

    def test_memory_statistics_tracking(self, orchestrator_agent):
        """Test memory statistics tracking functionality."""
        # Get initial memory statistics
        stats = orchestrator_agent.get_memory_statistics()

        assert isinstance(stats, dict)
        assert "current_states" in stats
        assert "active_states" in stats
        assert "completed_states" in stats
        assert "failed_states" in stats
        assert "memory_utilization_percent" in stats
        assert "cleanup_stats" in stats

        # Verify cleanup stats structure
        cleanup_stats = stats["cleanup_stats"]
        expected_keys = [
            "total_cleanups",
            "states_removed_ttl",
            "states_removed_limit",
            "max_states_held",
            "avg_cleanup_duration_ms",
        ]
        for key in expected_keys:
            assert key in cleanup_stats

    def test_enhanced_cleanup_functionality(self, orchestrator_agent):
        """Test enhanced memory cleanup with statistics tracking."""
        from datetime import datetime, timedelta

        from omnibase_core.agents.models.model_orchestrator_execution_state import (
            ModelOrchestratorExecutionState,
        )

        # Add some test execution states
        old_time = datetime.now() - timedelta(hours=2)
        for i in range(5):
            state = ModelOrchestratorExecutionState(
                scenario_id=f"old-scenario-{i}",
                status=EnumWorkflowStatus.COMPLETED,
                start_time=old_time,
                end_time=old_time + timedelta(minutes=5),
                correlation_id=f"corr-{i}",
                operation_type="test",
            )
            orchestrator_agent._execution_states[f"old-scenario-{i}"] = state

        initial_count = len(orchestrator_agent._execution_states)

        # Force cleanup by setting last cleanup time to past
        orchestrator_agent._last_cleanup_time = datetime.now() - timedelta(minutes=10)

        # Trigger cleanup
        orchestrator_agent._cleanup_execution_states_if_needed()

        # Verify cleanup occurred
        assert len(orchestrator_agent._execution_states) <= initial_count
        assert orchestrator_agent._cleanup_stats["total_cleanups"] > 0


class TestModelOrchestratorParameters:
    """Test suite for ModelOrchestratorParameters."""

    def test_parameter_creation(self):
        """Test creating orchestrator parameters."""
        params = ModelOrchestratorParameters(
            scenario_id="test-scenario",
            correlation_id="test-correlation",
            execution_mode="parallel",
            timeout_seconds=600,
            retry_count=5,
            metadata={"key": "value"},
        )

        assert params.scenario_id == "test-scenario"
        assert params.correlation_id == "test-correlation"
        assert params.execution_mode == "parallel"
        assert params.timeout_seconds == 600
        assert params.retry_count == 5
        assert params.metadata == {"key": "value"}

    def test_parameter_defaults(self):
        """Test default parameter values."""
        params = ModelOrchestratorParameters(
            scenario_id="test-scenario", correlation_id="test-correlation"
        )

        assert params.execution_mode == "sequential"
        assert params.timeout_seconds == 300
        assert params.retry_count == 3
        assert params.metadata is None

    def test_metadata_operations(self):
        """Test metadata getter and setter operations."""
        params = ModelOrchestratorParameters(
            scenario_id="test-scenario", correlation_id="test-correlation"
        )

        # Test with no metadata initially
        assert params.get_metadata_value("key", "default") == "default"
        assert not params.has_metadata("key")

        # Set metadata value
        params.set_metadata_value("key", "value")
        assert params.get_metadata_value("key") == "value"
        assert params.has_metadata("key")

        # Test with existing metadata
        params.metadata = {"existing": "value"}
        params.set_metadata_value("new_key", "new_value")
        assert params.get_metadata_value("existing") == "value"
        assert params.get_metadata_value("new_key") == "new_value"
        assert params.has_metadata("existing")
        assert params.has_metadata("new_key")
