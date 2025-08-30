"""
Pydantic model for node execution results.

Defines the structured result model for node execution operations
within the ONEX architecture.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_base_result import ModelBaseResult


class ModelExecutionData(BaseModel):
    """Execution data from node operations."""

    # Common execution results
    result_type: str | None = Field(
        None,
        description="Type of result (success, error, warning)",
    )
    result_code: int | None = Field(None, description="Numeric result code")
    result_message: str | None = Field(
        None,
        description="Human-readable result message",
    )

    # Output data
    output_text: str | None = Field(None, description="Text output from execution")
    output_json: dict[str, Any] | None = Field(
        None,
        description="Structured JSON output",
    )
    output_files: list[str] = Field(
        default_factory=list,
        description="List of generated files",
    )

    # Error information
    error_type: str | None = Field(None, description="Type of error if any")
    error_details: str | None = Field(None, description="Detailed error information")
    stack_trace: str | None = Field(None, description="Stack trace for debugging")

    # Performance data
    steps_completed: int = Field(0, description="Number of steps completed")
    steps_total: int | None = Field(None, description="Total number of steps")
    memory_used_mb: float | None = Field(
        None,
        description="Memory used during execution",
    )

    # Node-specific results
    artifacts_created: list[str] = Field(
        default_factory=list,
        description="Created artifacts",
    )
    resources_modified: list[str] = Field(
        default_factory=list,
        description="Modified resources",
    )

    # Extensibility
    custom_results: dict[str, str] | None = Field(
        None,
        description="Node-specific results",
    )
    custom_metrics: dict[str, float] | None = Field(
        None,
        description="Node-specific metrics",
    )

    def is_success(self) -> bool:
        """Check if execution was successful."""
        return self.result_type == "success" or (
            self.result_code is not None and self.result_code == 0
        )

    def has_errors(self) -> bool:
        """Check if execution had errors."""
        return self.error_type is not None or self.result_type == "error"


class ModelNodeExecutionResult(ModelBaseResult):
    """
    Structured result model for node execution operations.

    Contains the results of executing ONEX nodes through the CLI
    or other execution mechanisms.
    """

    node_name: str = Field(..., description="Name of the executed node")
    node_version: str | None = Field(
        None,
        description="Version of the executed node",
    )
    execution_data: ModelExecutionData = Field(
        default_factory=ModelExecutionData,
        description="Execution output data",
    )
    execution_time_ms: float | None = Field(
        None,
        description="Execution time in milliseconds",
    )
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for tracking",
    )
    output_format: str = Field(
        default="dict",
        description="Format of the execution output",
    )
