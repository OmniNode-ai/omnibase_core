"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data.
"""

from typing import Dict, Optional

from pydantic import BaseModel, Field

from omnibase.model.core.model_schema_value import ModelSchemaValue


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context.

    This model can represent error context values without resorting to Any type usage.
    """

    # Common error context fields
    file_path: Optional[str] = Field(None, description="File path related to the error")
    line_number: Optional[int] = Field(
        None, description="Line number where error occurred"
    )
    column_number: Optional[int] = Field(
        None, description="Column number where error occurred"
    )
    function_name: Optional[str] = Field(
        None, description="Function where error occurred"
    )
    module_name: Optional[str] = Field(None, description="Module where error occurred")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")

    # Additional context as schema values
    additional_context: Dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional context information as schema values",
    )

    @classmethod
    def from_dict(cls, context: dict) -> "ModelErrorContext":
        """
        Create ModelErrorContext from a dictionary.

        Args:
            context: Dictionary of context values

        Returns:
            ModelErrorContext instance
        """
        # Extract known fields
        known_fields = {
            "file_path": context.get("file_path"),
            "line_number": context.get("line_number"),
            "column_number": context.get("column_number"),
            "function_name": context.get("function_name"),
            "module_name": context.get("module_name"),
            "stack_trace": context.get("stack_trace"),
        }

        # Remove None values
        known_fields = {k: v for k, v in known_fields.items() if v is not None}

        # Convert remaining fields to schema values
        additional_context = {}
        for key, value in context.items():
            if key not in known_fields:
                additional_context[key] = ModelSchemaValue.from_value(value)

        return cls(**known_fields, additional_context=additional_context)

    def to_dict(self) -> dict:
        """
        Convert back to dictionary representation.

        Returns:
            Dictionary representation of the context
        """
        result = {}

        # Add known fields if present
        if self.file_path is not None:
            result["file_path"] = self.file_path
        if self.line_number is not None:
            result["line_number"] = self.line_number
        if self.column_number is not None:
            result["column_number"] = self.column_number
        if self.function_name is not None:
            result["function_name"] = self.function_name
        if self.module_name is not None:
            result["module_name"] = self.module_name
        if self.stack_trace is not None:
            result["stack_trace"] = self.stack_trace

        # Add additional context
        for key, value in self.additional_context.items():
            result[key] = value.to_value()

        return result
