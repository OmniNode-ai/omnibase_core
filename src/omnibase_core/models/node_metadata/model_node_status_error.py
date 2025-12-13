"""
Node Status Error Model.

Error node status with error details for discriminated union pattern.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.typed_dict_error_summary import TypedDictErrorSummary


class ModelNodeStatusError(BaseModel):
    """Error node status with error details."""

    status_type: str = Field(
        default="error",
        description="Status discriminator",
    )
    error_code: str = Field(description="Error classification code")
    error_message: str = Field(description="Human-readable error description")
    recovery_suggestion: str | None = Field(
        default=None,
        description="Suggested recovery action",
    )

    def is_critical_error(self) -> bool:
        """Check if this is a critical error."""
        code_lower = self.error_code.lower()
        return any(keyword in code_lower for keyword in ["critical", "fatal", "system"])

    def has_recovery_suggestion(self) -> bool:
        """Check if recovery suggestion is available."""
        return self.recovery_suggestion is not None

    def get_error_severity(self) -> str:
        """Get error severity level."""
        if self.is_critical_error():
            return "critical"
        elif any(
            keyword in self.error_code.lower() for keyword in ["warning", "minor"]
        ):
            return "low"
        else:
            return "medium"

    def get_error_summary(self) -> TypedDictErrorSummary:
        """Get error status summary."""
        return {
            "status_type": self.status_type,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "has_recovery_suggestion": self.has_recovery_suggestion(),
            "recovery_suggestion": self.recovery_suggestion,
            "is_critical": self.is_critical_error(),
            "severity": self.get_error_severity(),
        }
