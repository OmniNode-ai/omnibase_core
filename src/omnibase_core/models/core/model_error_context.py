from typing import Any

from pydantic import Field

from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

"""
Model for representing error context with proper type safety.

This model replaces dict[str, Any]ionary usage in error contexts by providing
a structured representation of error context data.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_schema_value import ModelSchemaValue


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context.

    This model can represent error context values without resorting to Any type usage.
    """

    # Common error context fields
    file_path: str | None = Field(
        default=None, description="File path related to the error"
    )
    line_number: int | None = Field(
        default=None,
        description="Line number where error occurred",
    )
    column_number: int | None = Field(
        default=None,
        description="Column number where error occurred",
    )
    function_name: str | None = Field(
        default=None,
        description="Function where error occurred",
    )
    module_name: str | None = Field(
        default=None, description="Module where error occurred"
    )
    stack_trace: str | None = Field(
        default=None, description="Stack trace if available"
    )

    # Additional context as schema values
    additional_context: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional context information as schema values",
    )
