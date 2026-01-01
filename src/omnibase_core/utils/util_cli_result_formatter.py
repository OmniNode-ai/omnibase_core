"""
CLI Result Formatter Utility.

Provides formatting utilities for CLI result output, extracting
formatting logic from ModelCliResult to maintain separation of concerns.
"""

import json

from omnibase_core.models.cli.model_cli_output_data import ModelCliOutputData


class UtilCliResultFormatter:
    """
    Formatter for CLI result output.

    Provides methods for formatting CLI execution results into
    human-readable output, handling both text and structured data.
    Extracts formatting logic from ModelCliResult to maintain
    separation of concerns.

    Methods:
        format_output: Format CLI result output for display
        format_error: Format error information for display
        format_summary: Format execution summary for display

    Example:
        >>> from omnibase_core.utils import UtilCliResultFormatter
        >>> output = UtilCliResultFormatter.format_summary(
        ...     success=True, duration_ms=150, exit_code=0
        ... )
        >>> print(output)

    Thread Safety:
        This class is fully thread-safe. All methods are static and stateless,
        operating only on their input parameters and returning new strings.
        No instance state exists, so the class can be safely used from multiple
        threads without synchronization. See docs/guides/THREADING.md for more
        details.

    .. note::
        Previously named ``ModelCliResultFormatter``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Util``
        prefix indicates a utility class.
    """

    @staticmethod
    def format_output(output_text: str, output_data: ModelCliOutputData | None) -> str:
        """
        Format CLI result output for display.

        Attempts to format output in the following priority:
        1. Use output_text if available
        2. Format output_data as JSON if available
        3. Return empty string if no output

        Args:
            output_text: Human-readable output text
            output_data: Structured output data from execution

        Returns:
            str: Formatted output string
        """
        if output_text:
            return output_text

        if output_data:
            # Try to format structured data nicely
            try:
                return json.dumps(output_data.model_dump(), indent=2, default=str)
            except (TypeError, ValueError):
                return str(output_data)

        return ""

    @staticmethod
    def format_error(
        error_message: str | None,
        error_details: str | None = None,
        validation_errors: list[object] | None = None,
    ) -> str:
        """
        Format error information for display.

        Args:
            error_message: Primary error message
            error_details: Detailed error information
            validation_errors: List of validation errors

        Returns:
            str: Formatted error string
        """
        parts = []

        if error_message:
            parts.append(f"Error: {error_message}")

        if error_details:
            parts.append(f"Details: {error_details}")

        if validation_errors:
            parts.append(f"Validation Errors ({len(validation_errors)}):")
            for i, error in enumerate(validation_errors, 1):
                parts.append(f"  {i}. {error}")

        return "\n".join(parts) if parts else ""

    @staticmethod
    def format_summary(
        success: bool,
        duration_ms: int,
        exit_code: int,
        warnings: list[str] | None = None,
    ) -> str:
        """
        Format execution summary for display.

        Args:
            success: Whether execution was successful
            duration_ms: Execution duration in milliseconds
            exit_code: Process exit code
            warnings: List of warning messages

        Returns:
            str: Formatted summary string
        """
        status = "SUCCESS" if success else "FAILURE"
        parts = [
            f"Status: {status}",
            f"Exit Code: {exit_code}",
            f"Duration: {duration_ms}ms",
        ]

        if warnings:
            parts.append(f"Warnings ({len(warnings)}):")
            for warning in warnings:
                parts.append(f"  - {warning}")

        return "\n".join(parts)


__all__ = ["UtilCliResultFormatter"]
