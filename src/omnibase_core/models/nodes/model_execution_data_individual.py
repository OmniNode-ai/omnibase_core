"""
Execution data from node operations.

Contains detailed execution data with strongly typed enums for result classification.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.nodes.enum_execution_error_type import EnumExecutionErrorType
from omnibase_core.enums.nodes.enum_execution_result_type import EnumExecutionResultType
from omnibase_core.models.core.model_generic_metadata import ModelGenericMetadata


class ModelExecutionData(BaseModel):
    """Execution data from node operations."""

    # Common execution results with strongly typed enum
    result_type: EnumExecutionResultType | None = Field(
        None,
        description="Type of result (success, error, warning, etc.)",
    )
    result_code: int | None = Field(None, description="Numeric result code")
    result_message: str | None = Field(
        None,
        description="Human-readable result message",
    )

    # Output data
    output_text: str | None = Field(None, description="Text output from execution")
    output_json: ModelGenericMetadata | None = Field(
        None,
        description="Structured JSON output",
    )
    output_files: list[str] = Field(
        default_factory=list,
        description="List of generated files",
    )

    # Error information with strongly typed enum
    error_type: EnumExecutionErrorType | None = Field(
        None, description="Type of error if any"
    )
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
        return self.result_type == EnumExecutionResultType.SUCCESS or (
            self.result_code is not None and self.result_code == 0
        )

    def has_errors(self) -> bool:
        """Check if execution had errors."""
        return (
            self.error_type is not None
            or self.result_type == EnumExecutionResultType.ERROR
        )
