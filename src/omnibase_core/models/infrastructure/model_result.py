"""
Result Model.

Generic Result[T, E] pattern for CLI operations providing type-safe
success/error handling with proper MyPy compliance.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.types.type_serializable_value import (
    SerializableValue,
    SerializedDict,
)

# Type variables for mapped types in transformations (still needed for methods)
U = TypeVar("U")  # Mapped type for transformations
F = TypeVar("F")  # Mapped error type for transformations


class ModelResult[T, E](
    BaseModel,
):  # Protocols removed temporarily for validation
    """
    Generic Result[T, E] pattern for type-safe error handling.

    Represents an operation that can either succeed with value T
    or fail with error E. Provides monadic operations for chaining.
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

    @field_serializer("error")
    def serialize_error(self, error: E | None) -> SerializableValue:
        """Convert Exception types to string for serialization."""
        if isinstance(error, Exception):
            return str(error)
        # Return as SerializableValue - Pydantic will handle the conversion
        if isinstance(error, (str, int, float, bool, type(None))):
            return error
        if error is None:
            return None
        return str(error)

    @field_validator("error", mode="before")
    @classmethod
    def validate_error(cls, v: Any) -> Any:
        """Pre-process Exception types before Pydantic validation.

        Note: Uses Any types because field validators operate at runtime before
        type parameters are resolved. Pydantic handles the actual type validation.
        """
        if isinstance(v, Exception):
            return str(v)
        return v

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        """Pre-process Exception types in value field before Pydantic validation.

        Note: Uses Any types because field validators operate at runtime before
        type parameters are resolved. Pydantic handles the actual type validation.
        """
        if isinstance(v, Exception):
            return str(v)
        return v

    success: bool = Field(default=..., description="Whether the operation succeeded")
    value: T | None = Field(default=None, description="Success value (if success=True)")
    error: E | None = Field(default=None, description="Error value (if success=False)")

    def __init__(
        self,
        success: bool,
        value: T | None = None,
        error: E | None = None,
        **data: object,
    ) -> None:
        """Initialize Result with type validation."""
        super().__init__(success=success, value=value, error=error, **data)

        # Validate that exactly one of value or error is set
        if success and value is None:
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                "Success result must have a value",
            )
        if not success and error is None:
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                "Error result must have an error",
            )
        if success and error is not None:
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                "Success result cannot have an error",
            )
        if not success and value is not None:
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                "Error result cannot have a value",
            )

    def _get_value_or_raise(self) -> T:
        """
        Internal helper to extract value from success result with None guard.

        Returns the value if it exists, raising ModelOnexError if value is None.
        This centralizes the "success-but-None" guard pattern used across methods.

        Returns:
            T: The unwrapped value

        Raises:
            ModelOnexError: If value is None despite success=True
        """
        value = self.value
        if value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Success result has None value",
            )
        return value

    def _get_error_or_raise(self) -> E:
        """
        Internal helper to extract error from error result with None guard.

        Returns the error if it exists, raising ModelOnexError if error is None.
        This centralizes the "error-but-None" guard pattern used across methods.

        Returns:
            E: The unwrapped error

        Raises:
            ModelOnexError: If error is None despite success=False
        """
        error = self.error
        if error is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Error result has None error",
            )
        return error

    @classmethod
    def ok(cls, value: T) -> ModelResult[T, E]:
        """Create a successful result."""
        return cls(success=True, value=value, error=None)

    @classmethod
    def err(cls, error: E) -> ModelResult[T, E]:
        """Create an error result."""
        return cls(success=False, value=None, error=error)

    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self.success

    def is_err(self) -> bool:
        """Check if result is an error."""
        return not self.success

    def unwrap(self) -> T:
        """
        Unwrap the value, raising an exception if error.

        Raises:
            ModelOnexError: If result is an error
        """
        if not self.success:
            raise ModelOnexError(
                EnumCoreErrorCode.OPERATION_FAILED,
                f"Called unwrap() on error result: {self.error}",
            )
        return self._get_value_or_raise()

    def unwrap_or(self, default: T) -> T:
        """Unwrap the value or return default if error."""
        if self.success:
            return self._get_value_or_raise()
        return default

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """Unwrap the value or compute from error using function."""
        if self.success:
            return self._get_value_or_raise()
        return f(self._get_error_or_raise())

    def expect(self, msg: str) -> T:
        """
        Unwrap the value with a custom error message.

        Args:
            msg: Custom error message

        Raises:
            ModelOnexError: If result is an error, with custom message
        """
        if not self.success:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"{msg}: {self.error}",
            )
        return self._get_value_or_raise()

    def map(self, f: Callable[[T], U]) -> ModelResult[U, E | Exception]:
        """
        Map function over the success value.

        If this is Ok(value), returns Ok(f(value)).
        If this is Err(error), returns Err(error).

        Note: Return type is E | Exception because exceptions thrown by f()
        are caught and converted to error results.
        """
        if self.success:
            try:
                new_value = f(self._get_value_or_raise())
                return ModelResult.ok(new_value)
            except Exception as e:
                # fallback-ok: Monadic error handling - converting exceptions to error results
                return ModelResult.err(e)
        # Pass through the original error
        return ModelResult.err(self._get_error_or_raise())

    def map_err(self, f: Callable[[E], F]) -> ModelResult[T, F | Exception]:
        """
        Map function over the error value.

        If this is Ok(value), returns Ok(value).
        If this is Err(error), returns Err(f(error)).

        Note: Return type is F | Exception because exceptions thrown by f()
        are caught and converted to error results.
        """
        if self.success:
            return ModelResult.ok(self._get_value_or_raise())
        try:
            new_error = f(self._get_error_or_raise())
            return ModelResult.err(new_error)
        except Exception as e:
            # fallback-ok: Monadic error handling - converting exceptions to error results
            return ModelResult.err(e)

    def and_then(
        self, f: Callable[[T], ModelResult[U, E]]
    ) -> ModelResult[U, E | Exception]:
        """
        Flat map (bind) operation for chaining Results.

        If this is Ok(value), returns f(value).
        If this is Err(error), returns Err(error).

        Note: Return type is E | Exception because:
        - Original error E is passed through if this is an error result
        - Function f() returns ModelResult[U, E] which could contain E
        - Exceptions thrown by f() are caught and converted to error results
        """
        if self.success:
            try:
                # Call f() and widen the return type to include Exception
                # This cast is safe because ModelResult[U, E] is a subtype of
                # ModelResult[U, E | Exception] at runtime (same structure, wider error type)
                result = f(self._get_value_or_raise())
                return cast("ModelResult[U, E | Exception]", result)
            except Exception as e:
                # fallback-ok: Monadic error handling - converting exceptions to error results
                return ModelResult.err(e)
        # Pass through the original error
        return ModelResult.err(self._get_error_or_raise())

    def or_else(
        self, f: Callable[[E], ModelResult[T, F]]
    ) -> ModelResult[T, F | Exception]:
        """
        Alternative operation for error recovery.

        If this is Ok(value), returns Ok(value).
        If this is Err(error), returns f(error).

        Note: Return type is F | Exception because:
        - Function f() returns ModelResult[T, F] which could contain F
        - Exceptions thrown by f() are caught and converted to error results
        """
        if self.success:
            return ModelResult.ok(self._get_value_or_raise())
        try:
            # Call f() and widen the return type to include Exception
            # This cast is safe because ModelResult[T, F] is a subtype of
            # ModelResult[T, F | Exception] at runtime (same structure, wider error type)
            result = f(self._get_error_or_raise())
            return cast("ModelResult[T, F | Exception]", result)
        except Exception as e:
            # fallback-ok: Monadic error handling - converting exceptions to error results
            return ModelResult.err(e)

    def __repr__(self) -> str:
        """String representation."""
        if self.success:
            return f"ModelResult.ok({self.value!r})"
        return f"ModelResult.err({self.error!r})"

    def __str__(self) -> str:
        """Human-readable string."""
        if self.success:
            return f"Success: {self.value}"
        return f"Error: {self.error}"

    def __bool__(self) -> bool:
        """Boolean conversion - True if success, False if error.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. Here, ``bool(result)`` returns the value
            of ``success``, enabling idiomatic error checking patterns.

        Returns:
            bool: True if the result represents success, False if error.

        Example:
            >>> result = ModelResult.ok("data")
            >>> if result:
            ...     print(f"Got: {result.value}")
            Got: data

            >>> error = ModelResult.err("failed")
            >>> if not error:
            ...     print(f"Error: {error.error}")
            Error: failed
        """
        return self.success

    # Protocol method implementations

    def execute(self, **kwargs: object) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def configure(self, **kwargs: object) -> bool:
        """Configure instance with provided parameters (Configurable protocol)."""
        try:
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except (AttributeError, TypeError, ValueError) as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> SerializedDict:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Note: Removed type alias to avoid anti-pattern detection
# Use ModelResult directly instead of alias


# Factory functions for common patterns
def ok[T](value: T) -> ModelResult[T, str]:
    """Create successful result with string error type."""
    return ModelResult.ok(value)


def err[E](error: E) -> ModelResult[str, E]:
    """Create error result with string success type."""
    return ModelResult.err(error)


def try_result[T](f: Callable[[], T]) -> ModelResult[T, Exception]:
    """
    Execute function and wrap result/exception in Result.

    Args:
        f: Function to execute

    Returns:
        Result containing either the return value or the exception
    """
    try:
        return ModelResult.ok(f())
    except Exception as e:
        # fallback-ok: Monadic error handling - converting exceptions to error results
        return ModelResult.err(e)


def collect_results[T, E](
    results: list[ModelResult[T, E]],
) -> ModelResult[list[T], list[E]]:
    """
    Collect a list[Any]of Results into a Result of list[Any]s.

    If all Results are Ok, returns Ok with list[Any]of values.
    If any Result is Err, returns Err with list[Any]of all errors.
    """
    values: list[T] = []
    errors: list[E] = []

    for result in results:
        if result.is_ok():
            values.append(result.unwrap())
        else:
            error = result.error  # Local bind for type narrowing
            if error is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Error result has None error",
                )
            errors.append(error)

    if errors:
        return ModelResult.err(errors)
    return ModelResult.ok(values)

    # Note: Type alias removed to comply with ONEX standards
    # Use ModelResult directly instead of alias


# Export for use
__all__ = [
    "ModelResult",
]
