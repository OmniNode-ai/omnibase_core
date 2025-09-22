"""
Retry execution failure information model.

Type-safe failure information container that replaces dict[str, str | int | None]
with structured validation and proper type handling for retry execution failures.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ModelRetryFailureInfo(BaseModel):
    """
    Type-safe failure information container for retry executions.

    Replaces dict[str, str | int | None] with structured failure information
    that maintains type safety for retry execution debugging.
    """

    # Failure details
    last_error: str | None = Field(
        None,
        description="Last error message encountered",
    )

    last_status_code: int | None = Field(
        None,
        description="Last HTTP status code or error code",
    )

    attempts_made: int = Field(
        default=0,
        description="Number of attempts made",
    )

    @classmethod
    def from_retry_execution(
        cls,
        last_error: str | None,
        last_status_code: int | None,
        attempts_made: int,
    ) -> ModelRetryFailureInfo:
        """Create failure info from retry execution data."""
        return cls(
            last_error=last_error,
            last_status_code=last_status_code,
            attempts_made=attempts_made,
        )

    def has_error(self) -> bool:
        """Check if failure info contains error details."""
        return self.last_error is not None or self.last_status_code is not None

    def get_error_summary(self) -> str:
        """Get a summary of the error for logging."""
        if not self.has_error():
            return "No errors recorded"

        parts = []
        if self.last_error:
            parts.append(f"Error: {self.last_error}")
        if self.last_status_code:
            parts.append(f"Status: {self.last_status_code}")
        parts.append(f"Attempts: {self.attempts_made}")

        return "; ".join(parts)


# Export the model
__all__ = ["ModelRetryFailureInfo"]
