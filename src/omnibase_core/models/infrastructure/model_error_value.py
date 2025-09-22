"""
Error Value Model.

Discriminated union for error values following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from ...enums.enum_core_error_code import EnumCoreErrorCode
from ...exceptions.onex_error import OnexError


class ModelErrorValue(BaseModel):
    """
    Discriminated union for error values.

    Replaces str | Exception | None union with structured error handling.
    """

    error_type: Literal["string", "exception", "none"] = Field(
        description="Type discriminator for error value"
    )

    # Error value storage (only one should be populated)
    string_error: str | None = None
    exception_error: Any | None = None  # Use Any for Exception storage

    @model_validator(mode="after")
    def validate_single_error(self) -> "ModelErrorValue":
        """Ensure only one error value is set based on type discriminator."""
        if self.error_type == "string":
            if self.string_error is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="string_error must be set when error_type is 'string'",
                )
            if self.exception_error is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="exception_error must be None when error_type is 'string'",
                )
        elif self.error_type == "exception":
            if self.exception_error is None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="exception_error must be set when error_type is 'exception'",
                )
            if self.string_error is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="string_error must be None when error_type is 'exception'",
                )
        elif self.error_type == "none":
            if self.string_error is not None or self.exception_error is not None:
                raise OnexError(
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Both error values must be None when error_type is 'none'",
                )

        return self

    @classmethod
    def from_string(cls, error: str) -> "ModelErrorValue":
        """Create error value from string."""
        return cls(error_type="string", string_error=error)

    @classmethod
    def from_exception(cls, error: Exception) -> "ModelErrorValue":
        """Create error value from exception."""
        return cls(error_type="exception", exception_error=error)

    @classmethod
    def from_none(cls) -> "ModelErrorValue":
        """Create empty error value."""
        return cls(error_type="none")

    def get_error(self) -> Any:
        """Get the actual error value."""
        if self.error_type == "string":
            return self.string_error
        elif self.error_type == "exception":
            return self.exception_error
        else:
            return None


# Export the model
__all__ = ["ModelErrorValue"]