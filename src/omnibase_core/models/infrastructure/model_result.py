from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from pydantic import Field, field_validator

from omnibase_core.models.errors.model_onex_error import ModelOnexError

"""
Result Model.

Generic Result[T, E] pattern for CLI operations providing type-safe
success/error handling with proper MyPy compliance.
"""


from collections.abc import Callable as CallableABC
from typing import Any, cast

from pydantic import BaseModel, field_serializer

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Type variables for Result pattern
T = TypeVar("T")  # Success type
E = TypeVar("E")  # Error type
U = TypeVar("U")  # Mapped type for transformations
F = TypeVar("F")  # Mapped error type for transformations


class ModelResult(
    BaseModel,
    Generic[T, E],
):  # Protocols removed temporarily for validation
    """
    Generic Result[T, E] pattern for type-safe error handling.

    Represents an operation that can either succeed with value T
    or fail with error E. Provides monadic operations for chaining.
    Implements omnibase_spi protocols:
    - Executable: Execution management capabilities
    - Configurable: Configuration management capabilities
    - Serializable: Data serialization/deserialization
    """

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
        # Removed arbitrary_types_allowed - handle Exception types explicitly
    }

    @field_serializer("error")
    def serialize_error(self, error: Any) -> Any:
        """Convert Exception types to string for serialization."""
        if isinstance(error, Exception):
            return str(error)
        return error

    @field_validator("error", mode="before")
    @classmethod
    def validate_error(cls, v: Any) -> Any:
        """Pre-process Exception types before Pydantic validation."""
        if isinstance(v, Exception):
            return str(v)
        return v

    @field_validator("value", mode="before")
    @classmethod
    def validate_value(cls, v: Any) -> Any:
        """Pre-process Exception types in value field before Pydantic validation."""
        if isinstance(v, Exception):
            return str(v)
        return v

    success: bool = Field(default=..., description="Whether the operation succeeded")
    value: Any = Field(default=None, description="Success value (if success=True)")
    error: Any = Field(default=None, description="Error value (if success=False)")

    def __init__(
        self,
        success: bool,
        value: Any = None,
        error: Any = None,
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
            ValueError: If result is an error
        """
        if not self.success:
            raise ModelOnexError(
                EnumCoreErrorCode.OPERATION_FAILED,
                f"Called unwrap() on error result: {self.error}",
            )
        if self.value is None:
            raise ModelOnexError(
                EnumCoreErrorCode.VALIDATION_ERROR,
                "Success result has None value",
            )
        return cast(T, self.value)

    def unwrap_or(self, default: T) -> T:
        """Unwrap the value or return default if error."""
        if self.success:
            if self.value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Success result has None value",
                )
            return cast(T, self.value)
        return default

    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """Unwrap the value or compute from error using function."""
        if self.success:
            if self.value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Success result has None value",
                )
            return cast(T, self.value)
        if self.error is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Error result has None error",
            )
        return f(self.error)

    def expect(self, msg: str) -> T:
        """
        Unwrap the value with a custom error message.

        Args:
            msg: Custom error message

        Raises:
            ValueError: If result is an error, with custom message
        """
        if not self.success:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
                message=f"{msg}: {self.error}",
            )
        if self.value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Success result has None value",
            )
        return cast(T, self.value)

    def map(self, f: Callable[[T], U]) -> ModelResult[U, object]:
        """
        Map function over the success value.

        If this is Ok(value), returns Ok(f(value)).
        If this is Err(error), returns Err(error).
        """
        if self.success:
            try:
                if self.value is None:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Success result has None value",
                    )
                new_value = f(self.value)
                return ModelResult.ok(new_value)
            except Exception as e:
                # fallback-ok: Monadic error handling - converting exceptions to error results
                return ModelResult.err(e)
        if self.error is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Error result has None error",
            )
        # Return the original error without unsafe cast
        return ModelResult.err(self.error)

    def map_err(self, f: Callable[[E], F]) -> ModelResult[T, object]:
        """
        Map function over the error value.

        If this is Ok(value), returns Ok(value).
        If this is Err(error), returns Err(f(error)).
        """
        if self.success:
            if self.value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Success result has None value",
                )
            return ModelResult.ok(self.value)
        try:
            if self.error is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Error result has None error",
                )
            new_error = f(self.error)
            return ModelResult.err(new_error)
        except Exception as e:
            # fallback-ok: Monadic error handling - converting exceptions to error results
            return ModelResult.err(e)

    def and_then(self, f: Callable[[T], ModelResult[U, E]]) -> ModelResult[U, object]:
        """
        Flat map (bind) operation for chaining Results.

        If this is Ok(value), returns f(value).
        If this is Err(error), returns Err(error).
        """
        if self.success:
            try:
                if self.value is None:
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message="Success result has None value",
                    )
                result = f(self.value)
                # Cast to match the object return type signature
                return cast(ModelResult[U, object], result)
            except Exception as e:
                # fallback-ok: Monadic error handling - converting exceptions to error results
                return ModelResult.err(e)
        if self.error is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Error result has None error",
            )
        # Return the original error without unsafe cast
        return ModelResult.err(self.error)

    def or_else(self, f: Callable[[E], ModelResult[T, F]]) -> ModelResult[T, object]:
        """
        Alternative operation for error recovery.

        If this is Ok(value), returns Ok(value).
        If this is Err(error), returns f(error).
        """
        if self.success:
            if self.value is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Success result has None value",
                )
            return ModelResult.ok(self.value)
        try:
            if self.error is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Error result has None error",
                )
            result = f(self.error)
            # Cast to match the object return type signature
            return cast(ModelResult[T, object], result)
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
        """Boolean conversion - True if success, False if error."""
        return self.success

    # Protocol method implementations

    def execute(self, **kwargs: Any) -> bool:
        """Execute or update execution status (Executable protocol)."""
        try:
            # Update any relevant execution fields
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception as e:
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
        except Exception as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Operation failed: {e}",
            ) from e

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)


# Note: Removed type alias to avoid anti-pattern detection
# Use ModelResult directly instead of alias


# Factory functions for common patterns
def ok(value: T) -> ModelResult[T, str]:
    """Create successful result with string error type."""
    return ModelResult.ok(value)


def err(error: E) -> ModelResult[str, E]:
    """Create error result with string success type."""
    return ModelResult.err(error)


def try_result(f: Callable[[], T]) -> ModelResult[T, Exception]:
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


def collect_results(results: list[ModelResult[T, E]]) -> ModelResult[list[T], list[E]]:
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
            if result.error is None:
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Error result has None error",
                )
            errors.append(result.error)

    if errors:
        return ModelResult.err(errors)
    return ModelResult.ok(values)

    # Note: Type alias removed to comply with ONEX standards
    # Use ModelResult directly instead of alias


# Export for use
__all__ = [
    "ModelResult",
]
