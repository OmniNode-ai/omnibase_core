"""
Model for CLI execution results.

Replaces hand-written result classes with proper Pydantic models
for CLI tool execution operations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ...core.decorators import allow_any_type, allow_dict_str_any
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
            stdout=None,
            stderr=None,
            execution_time_ms=None,
            memory_usage_mb=None,
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
        **kwargs: Any,
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
        return cls(
            success=True,
            output_data=output_data
            or ModelCliOutputData(
                stdout=None,
                stderr=None,
                execution_time_ms=None,
                memory_usage_mb=None,
            ),
            tool_id=tool_id,
            tool_display_name=tool_display_name,
            execution_time_ms=execution_time_ms,
            status_code=0,
            **kwargs,
        )

    @classmethod
    def create_error(
        cls,
        error_message: str,
        tool_id: UUID | None = None,
        tool_display_name: str | None = None,
        status_code: int = 1,
        output_data: ModelCliOutputData | None = None,
        **kwargs: Any,
    ) -> ModelCliExecutionResult:
        """
        Create an error execution result.

        Args:
            error_message: Description of the error
            tool_id: UUID of tool that failed
            tool_display_name: Human-readable name of tool that failed
            status_code: Numeric error code
            output_data: Any partial output data
            **kwargs: Additional fields

        Returns:
            Error result instance
        """
        return cls(
            success=False,
            error_message=error_message,
            tool_id=tool_id,
            tool_display_name=tool_display_name,
            status_code=status_code,
            output_data=output_data
            or ModelCliOutputData(
                stdout=None,
                stderr=None,
                execution_time_ms=None,
                memory_usage_mb=None,
            ),
            **kwargs,
        )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "error_message": None,
                "output_data": {"result": "operation completed"},
                "tool_id": "550e8400-e29b-41d4-a716-446655440000",
                "tool_display_name": "tool_discovery",
                "execution_time_ms": 150.5,
                "status_code": 0,
                "warning_message": None,
            },
        },
    )
