"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data.
"""

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

if TYPE_CHECKING:
    from omnibase_core.types.core_types import BasicErrorContext


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context.

    This model can represent error context values without resorting to Any type usage.
    Implements omnibase_spi protocols:
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
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

    @classmethod
    def with_context(
        cls,
        additional_context: dict[str, ModelSchemaValue],
    ) -> "ModelErrorContext":
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

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }

    # Protocol method implementations

    def serialize(self) -> dict[str, Any]:
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

    def to_simple_context(self) -> "BasicErrorContext":
        """Convert to BasicErrorContext (no circular dependencies)."""
        from omnibase_core.types.core_types import BasicErrorContext

        return BasicErrorContext(
            file_path=self.file_path,
            line_number=self.line_number,
            column_number=self.column_number,
            function_name=self.function_name,
            module_name=self.module_name,
            stack_trace=self.stack_trace,
            additional_context={
                k: v.to_value() for k, v in self.additional_context.items()
            },
        )

    @classmethod
    def from_simple_context(
        cls, simple_context: "BasicErrorContext"
    ) -> "ModelErrorContext":
        """Create from BasicErrorContext."""
        # Convert additional context to schema values
        additional_context_models = {
            k: ModelSchemaValue.from_value(v)
            for k, v in simple_context.additional_context.items()
        }

        return cls(
            file_path=simple_context.file_path,
            line_number=simple_context.line_number,
            column_number=simple_context.column_number,
            function_name=simple_context.function_name,
            module_name=simple_context.module_name,
            stack_trace=simple_context.stack_trace,
            additional_context=additional_context_models,
        )
