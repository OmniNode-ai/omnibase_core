"""
Hub Execution Protocol for ONEX CLI Interface

Defines the protocol interface for hub workflow execution,
providing abstracted hub operations without direct tool imports.
"""

from typing import Protocol

from omnibase_core.models.core.model_cli_execution_result import ModelCliExecutionResult


class ProtocolHubExecution(Protocol):
    """
    Protocol interface for hub workflow execution.

    Provides abstracted hub execution capabilities for workflow
    operations without requiring direct tool imports.
    """

    def execute_workflow(
        self,
        domain: str,
        workflow_name: str,
        dry_run: bool = False,
        timeout: int | None = None,
        parameters: dict | None = None,
    ) -> ModelCliExecutionResult:
        """
        Execute a workflow in the specified domain hub.

        Args:
            domain: Hub domain (e.g., 'generation')
            workflow_name: Name of the workflow to execute
            dry_run: Perform dry run validation only
            timeout: Override workflow timeout
            parameters: Additional workflow parameters

        Returns:
            ModelCliExecutionResult with execution results
        """
        ...

    def get_hub_introspection(self, domain: str) -> ModelCliExecutionResult:
        """
        Get hub introspection data including available workflows.

        Args:
            domain: Hub domain to introspect

        Returns:
            ModelCliExecutionResult with introspection data including:
            - description: Hub description
            - coordination_mode: Hub coordination mode
            - workflows: Dictionary of available workflows with metadata
        """
        ...

    def validate_workflow(
        self,
        domain: str,
        workflow_name: str,
    ) -> ModelCliExecutionResult:
        """
        Validate a workflow exists and is executable.

        Args:
            domain: Hub domain
            workflow_name: Name of the workflow to validate

        Returns:
            ModelCliExecutionResult with validation results
        """
        ...
