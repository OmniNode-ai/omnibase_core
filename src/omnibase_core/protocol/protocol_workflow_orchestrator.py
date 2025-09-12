"""
Protocol interface for Workflow orchestrator tools.

This protocol defines the interface for tools that can orchestrate
complex workflows with event-driven coordination.
"""

from typing import TYPE_CHECKING, Protocol

from omnibase_core.models.core.model_onex_result import ModelOnexResult
from omnibase_core.models.workflow.model_workflow_execution_state import (
    ModelWorkflowExecutionState,
)
from omnibase_core.protocol.models.model_health_check_result import (
    ModelHealthCheckResult,
)
from omnibase_core.protocol.models.model_workflow_input_state import (
    ModelWorkflowInputState,
)
from omnibase_core.tools.workflow.models.model_workflow_parameters import (
    ModelWorkflowParameters,
)

if TYPE_CHECKING:
    from omnibase_core.protocol.protocol_node_registry import ProtocolNodeRegistry


class ProtocolWorkflowOrchestrator(Protocol):
    """
    Protocol for Workflow orchestrator tools that coordinate complex workflow execution.

    Workflow orchestrators manage the execution of multiple Workflow nodes, handle dependencies,
    and coordinate the overall workflow state across different operation types.
    """

    def set_registry(self, registry: "ProtocolNodeRegistry") -> None:
        """
        Set the registry for accessing other tools.

        Args:
            registry: The registry containing other tools and dependencies
        """
        ...

    def run(self, input_state: ModelWorkflowInputState) -> ModelOnexResult:
        """
        Run the Workflow orchestrator with the provided input state.

        Args:
            input_state: Input state containing action and parameters

        Returns:
            Result of Workflow orchestration
        """
        ...

    def orchestrate_operation(
        self,
        operation_type: str,
        scenario_id: str,
        correlation_id: str,
        parameters: ModelWorkflowParameters,
    ) -> ModelOnexResult:
        """
        Orchestrate a specific operation type.

        Args:
            operation_type: Type of operation (model_generation, bootstrap_validation, extraction, generic)
            scenario_id: ID of the scenario to orchestrate
            correlation_id: Correlation ID for tracking
            parameters: Additional parameters for the operation

        Returns:
            Result of operation orchestration
        """
        ...

    def get_execution_state(
        self,
        scenario_id: str,
    ) -> ModelWorkflowExecutionState | None:
        """
        Get the current execution state for a scenario.

        Args:
            scenario_id: ID of the scenario

        Returns:
            Current execution state or None if not found
        """
        ...

    def health_check(self) -> ModelHealthCheckResult:
        """
        Perform health check for the Workflow orchestrator.

        Returns:
            Health check result with status and capabilities
        """
        ...
