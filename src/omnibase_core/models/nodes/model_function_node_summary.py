"""
Function node summary model.

Clean, strongly-typed replacement for function node union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelFunctionNodeSummary(BaseModel):
    """
    Clean, strongly-typed model replacing function node union return types.

    Eliminates: dict[str, str | int | bool | float | list[str] | None]

    With proper structured data using specific field types.
    """

    # Core function info
    name: str = Field(..., description="Function name")
    description: str | None = Field(None, description="Function description")
    function_type: str = Field(default="function", description="Type of function")
    status: str = Field(default="active", description="Function status")
    complexity: str = Field(default="medium", description="Function complexity level")
    version: str = Field(default="1.0.0", description="Function version")

    # Function characteristics
    parameter_count: int = Field(default=0, description="Number of parameters")
    return_type: str | None = Field(None, description="Return type annotation")

    # Quality indicators
    has_documentation: bool = Field(default=False, description="Has documentation")
    has_examples: bool = Field(default=False, description="Has examples")
    has_type_annotations: bool = Field(
        default=False, description="Has type annotations"
    )
    has_tests: bool = Field(default=False, description="Has unit tests")

    # Organization
    tags: list[str] = Field(default_factory=list, description="Function tags")
    categories: list[str] = Field(
        default_factory=list, description="Function categories"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Function dependencies"
    )

    # Timestamps
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")
    last_validated: datetime | None = Field(
        None, description="Last validation timestamp"
    )

    # Performance metrics
    execution_count: int = Field(default=0, description="Number of executions")
    success_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Success rate (0-1)"
    )

    average_execution_time_ms: float = Field(
        default=0.0, description="Average execution time in milliseconds"
    )

    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")

    # Code quality metrics
    cyclomatic_complexity: int = Field(
        default=1, description="Cyclomatic complexity score"
    )

    lines_of_code: int = Field(default=0, description="Lines of code")


# Export the model
__all__ = ["ModelFunctionNodeSummary"]
