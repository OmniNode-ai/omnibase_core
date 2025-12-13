"""
Execution data model for node operations.

Contains detailed execution information including results, errors,
performance metrics, and node-specific artifacts.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelExecutionData(BaseModel):
    """Execution data from node operations."""

    # Common execution results
    result_type: str | None = Field(
        default=None,
        description="Type of result (success, error, warning)",
    )
    result_code: int | None = Field(default=None, description="Numeric result code")
    result_message: str | None = Field(
        default=None,
        description="Human-readable result message",
    )

    # Output data
    output_text: str | None = Field(
        default=None, description="Text output from execution"
    )
    output_json: SerializedDict | None = Field(
        default=None,
        description="Structured JSON output",
    )
    output_files: list[str] = Field(
        default_factory=list,
        description="List of generated files",
    )

    # Error information
    error_type: str | None = Field(default=None, description="Type of error if any")
    error_details: str | None = Field(
        default=None, description="Detailed error information"
    )
    stack_trace: str | None = Field(
        default=None, description="Stack trace for debugging"
    )

    # Performance data
    steps_completed: int = Field(default=0, description="Number of steps completed")
    steps_total: int | None = Field(default=None, description="Total number of steps")
    memory_used_mb: float | None = Field(
        default=None,
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
        default=None,
        description="Node-specific results",
    )
    custom_metrics: dict[str, float] | None = Field(
        default=None,
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
