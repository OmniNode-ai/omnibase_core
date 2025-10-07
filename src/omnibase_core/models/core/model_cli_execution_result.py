from pydantic import Field

"""
Model for CLI execution results.

Replaces hand-written result classes with proper Pydantic models
for CLI tool execution operations.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.utils.decorators import allow_any_type, allow_dict_str_any


@allow_dict_str_any("CLI execution results must handle diverse tool output types")
@allow_any_type("CLI execution results need flexible typing for tool interoperability")
class ModelCliExecutionResult(BaseModel):
    """
    Model for CLI tool execution results.

    Provides standardized result structure for CLI operations
    with proper type safety and validation.
    """

    # Core result information
    success: bool = Field(default=..., description="Whether the operation succeeded")
    error_message: str | None = Field(
        default=None,
        description="Error message if operation failed",
    )

    # Output data
    output_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool execution output data",
    )

    # Execution metadata
    tool_name: str | None = Field(
        default=None,
        description="Name of the tool that was executed",
    )
    execution_time_ms: float | None = Field(
        default=None,
        description="Execution time in milliseconds",
    )

    # Status information
    status_code: int = Field(default=0, description="Numeric status code (0 = success)")
    warning_message: str | None = Field(
        default=None,
        description="Warning message if applicable",
    )

    @classmethod
    def create_success(
        cls,
        output_data: dict[str, Any] | None = None,
        tool_name: str | None = None,
        execution_time_ms: float | None = None,
        **kwargs: Any,
    ) -> "ModelCliExecutionResult":
        """
        Create a successful execution result.

        Args:
            output_data: Tool execution output
            tool_name: Name of executed tool
            execution_time_ms: Execution duration
            **kwargs: Additional fields

        Returns:
            Success result instance
        """
        return cls(
            success=True,
            output_data=output_data or {},
            tool_name=tool_name,
            execution_time_ms=execution_time_ms,
            status_code=0,
            **kwargs,
        )

    @classmethod
    def create_error(
        cls,
        error_message: str,
        tool_name: str | None = None,
        status_code: int = 1,
        output_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ModelCliExecutionResult":
        """
        Create an error execution result.

        Args:
            error_message: Description of the error
            tool_name: Name of tool that failed
            status_code: Numeric error code
            output_data: Any partial output data
            **kwargs: Additional fields

        Returns:
            Error result instance
        """
        return cls(
            success=False,
            error_message=error_message,
            tool_name=tool_name,
            status_code=status_code,
            output_data=output_data or {},
            **kwargs,
        )
