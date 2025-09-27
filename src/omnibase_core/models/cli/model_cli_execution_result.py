"""
Model for CLI execution results.

Replaces hand-written result classes with proper Pydantic models
for CLI tool execution operations.
"""

from __future__ import annotations

# Removed Any import - using object for ONEX compliance
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.decorators import allow_any_type, allow_dict_str_any

from .model_cli_output_data import ModelCliOutputData


@allow_dict_str_any("CLI execution results must handle diverse tool output types")
@allow_any_type("CLI execution results need flexible typing for tool interoperability")
class ModelCliExecutionResult(BaseModel):
    """
    Model for CLI tool execution results.

    Provides standardized result structure for CLI operations
    with proper type safety and validation.
    """

    # Core result information
    success: bool = Field(..., description="Whether the operation succeeded")
    error_message: str | None = Field(
        None,
        description="Error message if operation failed",
    )

    # Output data
    output_data: ModelCliOutputData = Field(
        default_factory=lambda: ModelCliOutputData(
            stdout="",
            stderr="",
            execution_time_ms=0.0,
            memory_usage_mb=0.0,
        ),
        description="Tool execution output data",
    )

    # Execution metadata - Entity reference with UUID
    tool_id: UUID | None = Field(
        None,
        description="Unique identifier of the tool that was executed",
    )
    tool_display_name: str | None = Field(
        None,
        description="Human-readable name of the tool that was executed",
    )
    execution_time_ms: float | None = Field(
        None,
        description="Execution time in milliseconds",
    )

    # Status information
    status_code: int = Field(0, description="Numeric status code (0 = success)")
    warning_message: str | None = Field(
        None,
        description="Warning message if applicable",
    )

    @classmethod
    def create_success(
        cls,
        output_data: ModelCliOutputData | None = None,
        tool_id: UUID | None = None,
        tool_display_name: str | None = None,
        execution_time_ms: float | None = None,
        **kwargs: object,
    ) -> ModelCliExecutionResult:
        """
        Create a successful execution result.

        Args:
            output_data: Tool execution output
            tool_id: UUID of executed tool
            tool_display_name: Human-readable name of executed tool
            execution_time_ms: Execution duration
            **kwargs: Additional fields

        Returns:
            Success result instance
        """
        # Extract known fields with proper types from kwargs
        warning_message = kwargs.get("warning_message", None)

        # Type validation for extracted kwargs
        if warning_message is not None and not isinstance(warning_message, str):
            warning_message = None

        return cls(
            success=True,
            error_message=None,
            output_data=output_data
            or ModelCliOutputData(
                stdout="",
                stderr="",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
            ),
            tool_id=tool_id,
            tool_display_name=tool_display_name,
            execution_time_ms=execution_time_ms,
            status_code=0,
            warning_message=warning_message,
        )

    @classmethod
    def create_error(
        cls,
        error_message: str,
        tool_id: UUID | None = None,
        tool_display_name: str | None = None,
        status_code: int = 1,
        output_data: ModelCliOutputData | None = None,
        **kwargs: object,
    ) -> ModelCliExecutionResult:
        """
        Create an error execution result.

        Args:
            error_message: Description of the error
            tool_id: UUID of tool that failed
            tool_display_name: Human-readable name of tool that failed
            status_code: Numeric error code
            output_data: Partial output data if available
            **kwargs: Additional fields

        Returns:
            Error result instance
        """
        # Extract known fields with proper types from kwargs
        execution_time_ms = kwargs.get("execution_time_ms", None)
        warning_message = kwargs.get("warning_message", None)

        # Type validation for extracted kwargs
        if execution_time_ms is not None and not isinstance(
            execution_time_ms, (int, float)
        ):
            execution_time_ms = None
        if warning_message is not None and not isinstance(warning_message, str):
            warning_message = None

        return cls(
            success=False,
            error_message=error_message,
            tool_id=tool_id,
            tool_display_name=tool_display_name,
            status_code=status_code,
            output_data=output_data
            or ModelCliOutputData(
                stdout="",
                stderr="",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
            ),
            execution_time_ms=execution_time_ms,
            warning_message=warning_message,
        )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
