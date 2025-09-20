"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data.
"""

from pydantic import BaseModel, Field

from .model_schema_value import ModelSchemaValue


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context.

    This model can represent error context values without resorting to Any type usage.
    """

    # Common error context fields
    file_path: str | None = Field(None, description="File path related to the error")
    line_number: int | None = Field(
        None,
        description="Line number where error occurred",
    )
    column_number: int | None = Field(
        None,
        description="Column number where error occurred",
    )
    function_name: str | None = Field(
        None,
        description="Function where error occurred",
    )
    module_name: str | None = Field(None, description="Module where error occurred")
    stack_trace: str | None = Field(None, description="Stack trace if available")

    # Additional context as schema values
    additional_context: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional context information as schema values",
    )
