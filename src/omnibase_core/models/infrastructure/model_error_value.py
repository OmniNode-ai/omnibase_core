"""
Error Value Model.

Discriminated union for error values following ONEX one-model-per-file architecture.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_error_value_type import EnumErrorValueType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import SerializedDict


class ModelErrorValue(BaseModel):
    """
    Discriminated union for error values.

    Replaces str | Exception | None union with structured error handling.
    Implements Core protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    error_type: EnumErrorValueType = Field(
        description="Type discriminator for error value",
    )

    # Error value storage (only one should be populated)
    string_error: str | None = None
    exception_class: str | None = None  # Exception class name
    exception_message: str | None = None  # Exception message
    exception_traceback: str | None = None  # Exception traceback if available

    @model_validator(mode="after")
    def validate_single_error(self) -> ModelErrorValue:
        """Ensure only one error value is set based on type discriminator."""
        if self.error_type == EnumErrorValueType.STRING:
            if self.string_error is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="string_error must be set when error_type is 'string'",
                )
            if any(
                [
                    self.exception_class,
                    self.exception_message,
                    self.exception_traceback,
                ],
            ):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="exception fields must be None when error_type is 'string'",
                )
        elif self.error_type == EnumErrorValueType.EXCEPTION:
            if self.exception_class is None or self.exception_message is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="exception_class and exception_message must be set when error_type is 'exception'",
                )
            if self.string_error is not None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="string_error must be None when error_type is 'exception'",
                )
        elif self.error_type == EnumErrorValueType.NONE:
            if any(
                [
                    self.string_error,
                    self.exception_class,
                    self.exception_message,
                    self.exception_traceback,
                ],
            ):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="All error values must be None when error_type is 'none'",
                )

        return self

    @classmethod
    def from_string(cls, error: str) -> ModelErrorValue:
        """Create error value from string."""
        return cls(error_type=EnumErrorValueType.STRING, string_error=error)

    @classmethod
    def from_exception(cls, error: Exception) -> ModelErrorValue:
        """Create error value from exception."""
        import traceback

        return cls(
            error_type=EnumErrorValueType.EXCEPTION,
            exception_class=type(error).__name__,
            exception_message=str(error),
            exception_traceback=(
                traceback.format_exc()
                if hasattr(error, "__traceback__") and error.__traceback__
                else None
            ),
        )

    @classmethod
    def from_none(cls) -> ModelErrorValue:
        """Create empty error value."""
        return cls(error_type=EnumErrorValueType.NONE)

    def get_error(self) -> str | None:
        """Get the actual error value as a string representation."""
        if self.error_type == EnumErrorValueType.STRING:
            return self.string_error
        if self.error_type == EnumErrorValueType.EXCEPTION:
            return f"{self.exception_class}: {self.exception_message}"
        return None

    def get_exception_info(self) -> dict[str, str | None]:
        """Get structured exception information."""
        if self.error_type == EnumErrorValueType.EXCEPTION:
            return {
                "class": self.exception_class,
                "message": self.exception_message,
                "traceback": self.exception_traceback,
            }
        return {}

    def recreate_exception(self) -> Exception | None:
        """Attempt to recreate the original exception (best effort)."""
        if self.error_type != EnumErrorValueType.EXCEPTION:
            return None

        if not self.exception_class or not self.exception_message:
            return None

        # Try to recreate common exception types
        try:
            exception_classes: dict[str, type[Exception]] = {
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
                "AttributeError": AttributeError,
                "FileNotFoundError": FileNotFoundError,
                "RuntimeError": RuntimeError,
            }

            if self.exception_class in exception_classes:
                return exception_classes[self.exception_class](self.exception_message)
            # Fall back to generic RuntimeError with original class info
            return RuntimeError(f"{self.exception_class}: {self.exception_message}")
        except (AttributeError, TypeError, ValueError) as e:
            # If recreation fails, raise error with context about the failure
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Failed to recreate exception {self.exception_class}: {e}",
            ) from e

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If execution logic fails
        """
        # Update any relevant execution fields
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol).

        Raises:
            AttributeError: If setting an attribute fails
            Exception: If configuration logic fails
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


__all__ = ["ModelErrorValue"]
