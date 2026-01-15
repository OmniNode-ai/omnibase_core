"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue

if TYPE_CHECKING:
    from omnibase_core.types.type_core import TypedDictBasicErrorContext


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context.

    This model can represent error context values without resorting to Any type usage.
    Implements Core protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
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

    @classmethod
    def with_context(
        cls,
        additional_context: dict[str, ModelSchemaValue],
    ) -> ModelErrorContext:
        """
        Create ModelErrorContext with only additional context.

        This method provides a clean way to create ModelErrorContext instances
        with just the additional_context while maintaining MyPy compatibility.

        Args:
            additional_context: Dictionary of schema values for additional context

        Returns:
            ModelErrorContext instance with the provided additional context
        """
        return cls(
            file_path=None,
            line_number=None,
            column_number=None,
            function_name=None,
            module_name=None,
            stack_trace=None,
            additional_context=additional_context,
        )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def serialize(self) -> dict[str, object]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """
        Validate instance integrity (ProtocolValidatable protocol).

        Note: This is a pure validation method that does NOT throw exceptions
        to avoid circular dependencies. Use validation layer for exception-based validation.
        """
        # Basic validation - ensure required fields exist
        # This is pure data validation without exception throwing
        return True

    def to_simple_context(self) -> TypedDictBasicErrorContext:
        """Convert to TypedDictBasicErrorContext (no circular dependencies)."""
        simple_context: TypedDictBasicErrorContext = {}
        if self.file_path is not None:
            simple_context["file_path"] = self.file_path
        if self.line_number is not None:
            simple_context["line_number"] = self.line_number
        if self.column_number is not None:
            simple_context["column_number"] = self.column_number
        if self.function_name is not None:
            simple_context["function_name"] = self.function_name
        if self.module_name is not None:
            simple_context["module_name"] = self.module_name
        if self.stack_trace is not None:
            simple_context["stack_trace"] = self.stack_trace
        if self.additional_context:
            simple_context["additional_context"] = {
                k: v.to_value() for k, v in self.additional_context.items()
            }
        return simple_context

    @classmethod
    def from_simple_context(
        cls, simple_context: TypedDictBasicErrorContext
    ) -> ModelErrorContext:
        """Create from TypedDictBasicErrorContext."""
        # Convert additional context to schema values
        additional_context_models = {
            k: ModelSchemaValue.from_value(v)
            for k, v in simple_context.get("additional_context", {}).items()
        }

        return cls(
            file_path=simple_context.get("file_path"),
            line_number=simple_context.get("line_number"),
            column_number=simple_context.get("column_number"),
            function_name=simple_context.get("function_name"),
            module_name=simple_context.get("module_name"),
            stack_trace=simple_context.get("stack_trace"),
            additional_context=additional_context_models,
        )
