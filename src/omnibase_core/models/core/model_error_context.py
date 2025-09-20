"""
Model for representing error context with proper type safety.

This model replaces dictionary usage in error contexts by providing
a structured representation of error context data with proper enums
for severity and categorization.
"""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from omnibase_core.enums.enum_error_category import EnumErrorCategory
from omnibase_core.enums.enum_validation_severity import EnumValidationSeverity
from .model_schema_value import ModelSchemaValue


class ModelErrorContext(BaseModel):
    """
    Type-safe representation of error context with proper categorization and severity.

    This model provides structured error context without resorting to Any type usage,
    using strong typing with enums for categorization and severity levels.
    """

    # Error categorization and severity
    category: EnumErrorCategory = Field(
        EnumErrorCategory.UNKNOWN,
        description="Error category for proper handling strategy"
    )
    severity: EnumValidationSeverity = Field(
        EnumValidationSeverity.ERROR,
        description="Error severity level"
    )

    # Correlation and tracking
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique correlation ID for tracking"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error context was created"
    )

    # Location information (using Path instead of str)
    file_path: Path | None = Field(None, description="File path related to the error")
    line_number: int | None = Field(
        None,
        description="Line number where error occurred",
        ge=1
    )
    column_number: int | None = Field(
        None,
        description="Column number where error occurred",
        ge=1
    )

    # Code context
    function_name: str | None = Field(
        None,
        description="Function where error occurred",
        max_length=256
    )
    module_name: str | None = Field(
        None,
        description="Module where error occurred",
        max_length=256
    )
    class_name: str | None = Field(
        None,
        description="Class where error occurred",
        max_length=256
    )

    # Stack and debugging information
    stack_trace: str | None = Field(
        None,
        description="Stack trace if available",
        max_length=8192
    )
    error_message: str | None = Field(
        None,
        description="Detailed error message",
        max_length=1024
    )

    # Operation context
    operation_name: str | None = Field(
        None,
        description="Name of operation that failed",
        max_length=128
    )
    operation_id: UUID | None = Field(
        None,
        description="Unique operation identifier"
    )

    # Additional context as schema values
    additional_context: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional context information as typed schema values",
    )

    # User and session context
    user_id: str | None = Field(
        None,
        description="User ID if error is user-related",
        max_length=64
    )
    session_id: str | None = Field(
        None,
        description="Session ID if error is session-related",
        max_length=64
    )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary representation for logging."""
        result: dict[str, object] = {
            "category": self.category.value,
            "severity": self.severity.value,
            "correlation_id": str(self.correlation_id),
            "timestamp": self.timestamp.isoformat(),
        }

        # Add optional fields if they exist
        optional_fields = [
            "file_path", "line_number", "column_number", "function_name",
            "module_name", "class_name", "stack_trace", "error_message",
            "operation_name", "operation_id", "user_id", "session_id"
        ]

        for field in optional_fields:
            value = getattr(self, field)
            if value is not None:
                if isinstance(value, Path):
                    result[field] = str(value)
                elif isinstance(value, UUID):
                    result[field] = str(value)
                else:
                    result[field] = value

        # Add additional context
        if self.additional_context:
            from .model_schema_value import ModelSchemaValueFactory
            additional_context_dict: dict[str, object] = {
                k: ModelSchemaValueFactory.to_value(v)
                for k, v in self.additional_context.items()
            }
            result["additional_context"] = additional_context_dict

        return result

    def is_critical(self) -> bool:
        """Check if error context indicates critical severity."""
        return self.severity == EnumValidationSeverity.CRITICAL

    def is_retryable(self) -> bool:
        """Check if error context indicates a retryable error."""
        retryable_categories = {
            EnumErrorCategory.TRANSIENT,
            EnumErrorCategory.NETWORK,
            EnumErrorCategory.EXTERNAL_SERVICE,
        }
        return self.category in retryable_categories

    def add_context(self, key: str, value: object) -> None:
        """Add additional context information."""
        from .model_schema_value import ModelSchemaValueFactory
        self.additional_context[key] = ModelSchemaValueFactory.from_value(value)