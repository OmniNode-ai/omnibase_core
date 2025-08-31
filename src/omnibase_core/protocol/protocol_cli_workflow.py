"""
CLI Workflow Protocol for ONEX CLI Interface

Defines the protocol interface for CLI workflow discovery and execution,
providing abstracted workflow operations without direct tool imports.
"""

from typing import Protocol

from omnibase_core.model.core.model_cli_execution_result import ModelCliExecutionResult


class ProtocolCliWorkflow(Protocol):
    """
    Protocol interface for CLI workflow operations.

    Provides abstracted workflow discovery and execution capabilities
    for the CLI without requiring direct tool imports.
    """

    def list_workflows(self, domain: str | None = None) -> ModelCliExecutionResult:
        """
        List available workflows for a domain.

        Args:
            domain: Domain to filter workflows (e.g., 'generation')

        Returns:
            ModelCliExecutionResult with workflow data
        """
        ...

    def execute_workflow(
        self,
        domain: str,
        workflow_name: str,
        dry_run: bool = False,
        timeout: int | None = None,
        parameters: dict | None = None,
    ) -> ModelCliExecutionResult:
        """
        Execute a workflow in the specified domain.

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

    def get_workflow_info(
        self,
        domain: str,
        workflow_name: str,
    ) -> ModelCliExecutionResult:
        """
        Get detailed information about a specific workflow.

        Args:
            domain: Hub domain
            workflow_name: Name of the workflow

        Returns:
            ModelCliExecutionResult with workflow information
        """
        ...

    def list_domains(self) -> ModelCliExecutionResult:
        """
        List available workflow domains.

        Returns:
            ModelCliExecutionResult with available domains
        """
        ...
