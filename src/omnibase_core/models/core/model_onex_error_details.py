"""
ONEX Error Details Model.

Detailed error information for ONEX replies with context and resolution suggestions.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelOnexErrorDetails(BaseModel):
    """Detailed error information for Onex replies."""

    error_code: str = Field(description="Machine-readable error code")
    error_message: str = Field(description="Human-readable error message")
    error_type: str = Field(description="Error classification")
    stack_trace: str | None = Field(
        default=None,
        description="Stack trace if available",
    )
    additional_context: dict[str, str] = Field(
        default_factory=dict,
        description="Additional error context",
    )
    resolution_suggestions: list[str] = Field(
        default_factory=list,
        description="Suggested resolution steps",
    )

    def add_context(self, key: str, value: str) -> "ModelOnexErrorDetails":
        """Add additional context to error details."""
        new_context = {**self.additional_context, key: value}
        return self.model_copy(update={"additional_context": new_context})

    def add_resolution_suggestion(self, suggestion: str) -> "ModelOnexErrorDetails":
        """Add a resolution suggestion."""
        new_suggestions = [*self.resolution_suggestions, suggestion]
        return self.model_copy(update={"resolution_suggestions": new_suggestions})

    def get_severity(self) -> str:
        """Get error severity based on error type."""
        error_type_lower = self.error_type.lower()
        if "critical" in error_type_lower:
            return "critical"
        elif "validation" in error_type_lower:
            return "validation"
        elif (
            "authentication" in error_type_lower or "authorization" in error_type_lower
        ):
            return "security"
        elif "network" in error_type_lower:
            return "network"
        elif "timeout" in error_type_lower:
            return "timeout"
        else:
            return "general"

    def is_retriable(self) -> bool:
        """Check if error is retriable based on error type."""
        non_retriable_types = {
            "validation_error",
            "authentication_error",
            "authorization_error",
        }
        return self.error_type.lower() not in non_retriable_types

    def to_dict(self) -> SerializedDict:
        """Convert to dictionary representation."""
        return self.model_dump()

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        error_code: str | None = None,
        error_type: str = "general_error",
    ) -> "ModelOnexErrorDetails":
        """Create error details from an exception."""
        return cls(
            error_code=error_code or type(exception).__name__,
            error_message=str(exception),
            error_type=error_type,
            stack_trace=getattr(exception, "__traceback__", None),
        )
