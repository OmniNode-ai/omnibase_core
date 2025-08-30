"""
CLI Service protocol for ONEX CLI operations.

This protocol defines the interface for CLI argument parsing, flag handling,
and command line integration as part of NODEBASE-001 Phase 4 deconstruction.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import List, Optional, Protocol

from omnibase_core.core.services.cli_service.v1_0_0.models.model_cli_result import \
    ModelCliResult


class ProtocolToolHealthResult(Protocol):
    """Protocol for tool health check results."""

    status: str
    message: str
    details: dict[str, str]


class ProtocolToolProcessResult(Protocol):
    """Protocol for tool process results."""

    status: str
    message: str
    output: str


class ProtocolToolInputState(Protocol):
    """Protocol for tool input state objects."""

    version: object


class ProtocolToolMetadata(Protocol):
    """Protocol for tool metadata."""

    name: str
    version: str
    description: str


class ProtocolTool(Protocol):
    """Protocol defining the interface for tools that can be used with CLI service."""

    def health_check(self) -> ProtocolToolHealthResult:
        """Optional health check method."""
        ...

    def process(self, input_state: ProtocolToolInputState) -> ProtocolToolProcessResult:
        """Optional process method."""
        ...

    def get_version(self) -> str:
        """Optional version method."""
        ...

    def get_tool_metadata(self) -> ProtocolToolMetadata:
        """Optional metadata method."""
        ...


class ProtocolCliService(Protocol):
    """
    Protocol for CLI service operations.

    Defines the interface for CLI argument parsing, flag handling,
    and command line integration extracted from ModelNodeBase.
    """

    def parse_command_line_arguments(
        self, args: Optional[List[str]] = None
    ) -> ModelCliResult:
        """
        Parse command line arguments and return structured result.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            ModelCliResult: Parsed CLI arguments and flags
        """
        ...

    def handle_health_check_flag(self, tool_instance: ProtocolTool) -> ModelCliResult:
        """
        Handle --health-check flag execution.

        Args:
            tool_instance: The tool instance to run health check on

        Returns:
            ModelCliResult: Health check result with appropriate exit code
        """
        ...

    def handle_introspect_flag(
        self, tool_instance: ProtocolTool, contract_path: Path
    ) -> ModelCliResult:
        """
        Handle --introspect flag execution.

        Args:
            tool_instance: The tool instance to introspect
            contract_path: Path to the contract file for introspection

        Returns:
            ModelCliResult: Introspection result with metadata
        """
        ...

    def convert_args_to_input_state(
        self, parsed_args: dict[str, str | int | bool], tool_instance: ProtocolTool
    ) -> ProtocolToolInputState:
        """
        Convert parsed CLI arguments to tool-specific input state.

        Args:
            parsed_args: Dictionary of parsed CLI arguments
            tool_instance: The tool instance for input state creation

        Returns:
            ProtocolToolInputState: Tool-specific input state object
        """
        ...

    def generate_help_text(
        self, tool_instance: ProtocolTool, contract_path: Path
    ) -> str:
        """
        Generate help text for the tool based on contract and CLI interface.

        Args:
            tool_instance: The tool instance
            contract_path: Path to the contract file

        Returns:
            str: Generated help text
        """
        ...

    def handle_cli_error(self, error: Exception, operation: str) -> ModelCliResult:
        """
        Handle CLI errors with appropriate exit codes and error messages.

        Args:
            error: The exception that occurred
            operation: The operation that failed

        Returns:
            ModelCliResult: Error result with appropriate exit code
        """
        ...

    def determine_exit_code(
        self, result: ProtocolToolProcessResult, error: Optional[Exception] = None
    ) -> int:
        """
        Determine appropriate CLI exit code from result or error.

        Args:
            result: The operation result
            error: Optional exception

        Returns:
            int: Appropriate CLI exit code
        """
        ...

    def should_run_health_check(self, args: Optional[List[str]] = None) -> bool:
        """
        Check if --health-check flag is present in arguments.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            bool: True if --health-check flag is present
        """
        ...

    def should_run_introspect(self, args: Optional[List[str]] = None) -> bool:
        """
        Check if --introspect flag is present in arguments.

        Args:
            args: Optional list of arguments (defaults to sys.argv)

        Returns:
            bool: True if --introspect flag is present
        """
        ...
