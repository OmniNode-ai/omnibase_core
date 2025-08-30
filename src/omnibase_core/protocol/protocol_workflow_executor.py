"""
Protocol interface for Workflow executor tools.

This protocol defines the interface for tools that execute specific
operations within workflows, such as model generation and bootstrap validation.
"""

from typing import TYPE_CHECKING, Any, Protocol

from omnibase_core.model.core.model_onex_result import ModelOnexResult

if TYPE_CHECKING:
    from omnibase_core.protocol.protocol_node_registry import ProtocolNodeRegistry


class ProtocolWorkflowExecutor(Protocol):
    """
    Protocol for Workflow executor tools that handle execution of specific
    operations within workflows.

    These tools perform the actual work of Workflow operations such as
    model generation, bootstrap validation, and tool extraction.
    """

    def set_registry(self, registry: "ProtocolNodeRegistry") -> None:
        """
        Set the registry for accessing other tools.

        Args:
            registry: The registry containing other tools and dependencies
        """
        ...

    def run(self, input_state: dict[str, Any]) -> ModelOnexResult:
        """
        Run the Workflow executor with the provided input state.

        Args:
            input_state: Input state containing action and parameters

        Returns:
            Result of Workflow execution
        """
        ...

    def execute_operation(
        self,
        operation_type: str,
        scenario_id: str,
        correlation_id: str,
        parameters: dict[str, Any],
    ) -> ModelOnexResult:
        """
        Execute a specific operation.

        Args:
            operation_type: Type of operation to execute
            scenario_id: ID of the scenario
            correlation_id: Correlation ID for tracking
            parameters: Parameters for the operation

        Returns:
            Result of operation execution
        """
        ...

    def supports_operation(self, operation_type: str) -> bool:
        """
        Check if this executor supports a specific operation type.

        Args:
            operation_type: Type of operation to check

        Returns:
            True if operation is supported
        """
        ...

    def get_supported_operations(self) -> list[str]:
        """
        Get list of supported operation types.

        Returns:
            List of supported operation type strings
        """
        ...

    def validate_parameters(
        self,
        operation_type: str,
        parameters: dict[str, Any],
    ) -> list[str]:
        """
        Validate parameters for a specific operation.

        Args:
            operation_type: Type of operation
            parameters: Parameters to validate

        Returns:
            List of validation errors (empty if valid)
        """
        ...

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check for the Workflow executor.

        Returns:
            Health check result with status and capabilities
        """
        ...
