"""
Retry execution failure information model.

Type-safe failure information container that replaces dict[str, str | int | None]
with structured validation and proper type handling for retry execution failures.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import Configurable


class ModelRetryFailureInfo(BaseModel):
    """
    Type-safe failure information container for retry executions.

    Replaces dict[str, str | int | None] with structured failure information
    that maintains type safety for retry execution debugging.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Failure details
    error_message: str | None = Field(
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
            error_message=last_error,
            last_status_code=last_status_code,
            attempts_made=attempts_made,
        )

    def has_error(self) -> bool:
        """Check if failure info contains error details."""
        return self.error_message is not None or self.last_status_code is not None

    def get_error_summary(self) -> str:
        """Get a summary of the error for logging."""
        if not self.has_error():
            return "No errors recorded"

        parts = []
        if self.error_message:
            parts.append(f"Error: {self.error_message}")
        if self.last_status_code:
            parts.append(f"Status: {self.last_status_code}")
        parts.append(f"Attempts: {self.attempts_made}")

        return "; ".join(parts)

    # Export the model

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelRetryFailureInfo"]
