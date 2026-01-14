"""
Retry execution failure information model.

Type-safe failure information container that replaces dict[str, str | int | None]
with structured validation and proper type handling for retry execution failures.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelRetryFailureInfo(BaseModel):
    """
    Type-safe failure information container for retry executions.

    Replaces dict[str, str | int | None] with structured failure information
    that maintains type safety for retry execution debugging.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    # Failure details - using ONEX types instead of union types
    error_message: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(""),
        description="Last error message encountered",
    )

    last_status_code: ModelSchemaValue = Field(
        default_factory=lambda: ModelSchemaValue.from_value(0),
        description="Last HTTP status code or error code",
    )

    attempts_made: int = Field(
        default=0,
        description="Number of attempts made",
    )

    @classmethod
    def from_retry_execution(
        cls,
        last_error: str,
        last_status_code: int,
        attempts_made: int,
    ) -> ModelRetryFailureInfo:
        """Create failure info from retry execution data."""
        return cls(
            error_message=ModelSchemaValue.from_value(last_error if last_error else ""),
            last_status_code=ModelSchemaValue.from_value(
                last_status_code if last_status_code else 0,
            ),
            attempts_made=attempts_made,
        )

    def has_error(self) -> bool:
        """Check if failure info contains error details."""
        error_msg_value = self.error_message.to_value()
        status_code_value = self.last_status_code.to_value()
        return (isinstance(error_msg_value, str) and error_msg_value != "") or (
            isinstance(status_code_value, int) and status_code_value != 0
        )

    def get_error_summary(self) -> str:
        """Get a summary of the error for logging."""
        if not self.has_error():
            return "No errors recorded"

        parts = []
        error_msg_value = self.error_message.to_value()
        status_code_value = self.last_status_code.to_value()

        if isinstance(error_msg_value, str) and error_msg_value:
            parts.append(f"Error: {error_msg_value}")
        if isinstance(status_code_value, int) and status_code_value != 0:
            parts.append(f"Status: {status_code_value}")
        parts.append(f"Attempts: {self.attempts_made}")

        return "; ".join(parts)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: Any) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelRetryFailureInfo"]
