"""
CLI Command Result Model.

Standard result implementation for CLI command execution results.
"""

from typing import Any, Dict, Protocol, runtime_checkable


@runtime_checkable
class ProtocolCliCommandResult(Protocol):
    """Protocol for CLI command execution results."""

    success: bool
    result_data: Dict[str, Any]
    error_message: str | None
    execution_time_ms: float


class ModelCliCommandResult:
    """Standard CLI command result implementation."""

    def __init__(
        self,
        success: bool,
        result_data: Dict[str, Any] | None = None,
        error_message: str | None = None,
        execution_time_ms: float = 0.0,
    ) -> None:
        """Initialize command result."""
        self.success = success
        self.result_data = result_data or {}
        self.error_message = error_message
        self.execution_time_ms = execution_time_ms

    @classmethod
    def success_result(
        cls,
        result_data: Dict[str, Any],
        execution_time_ms: float = 0.0,
    ) -> "ModelCliCommandResult":
        """Create success result."""
        return cls(
            success=True,
            result_data=result_data,
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def error_result(
        cls,
        error_message: str,
        execution_time_ms: float = 0.0,
    ) -> "ModelCliCommandResult":
        """Create error result."""
        return cls(
            success=False,
            error_message=error_message,
            execution_time_ms=execution_time_ms,
        )


# Export for use
__all__ = [
    "ProtocolCliCommandResult",
    "ModelCliCommandResult",
]