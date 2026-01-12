"""
Standard error handling decorators for ONEX framework.

This module provides decorators that eliminate error handling boilerplate
and ensure consistent error patterns across all tools, especially important
for agent-generated tools.

All decorators in this module follow the ONEX exception handling contract:
- Cancellation/exit signals (SystemExit, KeyboardInterrupt, GeneratorExit,
  asyncio.CancelledError) ALWAYS propagate - they are never caught.
- ModelOnexError is always re-raised as-is to preserve error context.
- Other exceptions are wrapped in ModelOnexError with appropriate error codes.
"""

import asyncio
import functools
from collections.abc import Callable
from typing import Any

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import VALIDATION_ERRORS
from omnibase_core.models.errors.model_onex_error import ModelOnexError


def _is_validation_error(exc: Exception) -> bool:
    """Determine if an exception represents a validation error.

    This function uses a multi-tier detection strategy, ordered from most
    reliable to least reliable:

    1. Type checking against VALIDATION_ERRORS tuple (TypeError, ValidationError,
       ValueError) - most reliable, covers standard Python and Pydantic errors.
    2. Duck typing for Pydantic ValidationError: checks for `errors` method
       (Pydantic v2) which returns structured error details.
    3. Duck typing for validation-like exceptions: checks for `errors` attribute
       as a list (common pattern in validation libraries).
    4. Exception class name check: if class name contains "Validation" or
       "validation", treat as validation error (more reliable than message check).

    Args:
        exc: The exception to check.

    Returns:
        True if the exception appears to be a validation error, False otherwise.
    """
    # Tier 1: Direct type check against known validation error types
    # This is the most reliable check and covers:
    # - TypeError: type coercion failures
    # - ValidationError: Pydantic validation failures
    # - ValueError: value constraint violations
    if isinstance(exc, VALIDATION_ERRORS):
        return True

    # Tier 2: Duck typing for Pydantic-style ValidationError
    # Pydantic v2 ValidationError has an `errors()` method that returns
    # a list of error dictionaries with 'loc', 'msg', 'type' keys.
    errors_attr = getattr(exc, "errors", None)
    if callable(errors_attr):
        return True

    # Tier 3: Duck typing for validation-like exceptions with errors list
    # Some validation libraries expose errors as a list attribute rather than method
    if isinstance(errors_attr, list) and errors_attr:
        return True

    # Tier 4: Exception class name heuristic
    # Check if exception class name indicates validation (more reliable than message)
    # e.g., ValidationError, SchemaValidationError, InputValidationException
    exc_class_name = type(exc).__name__
    if "validation" in exc_class_name.lower():
        return True

    return False


def standard_error_handling(
    operation_name: str = "operation",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that provides standard error handling pattern for ONEX tools.

    This decorator eliminates 6+ lines of boilerplate error handling code
    and ensures consistent error patterns. It's especially valuable for
    agent-generated tools that need reliable error handling.

    Args:
        operation_name: Human-readable name for the operation (used in error messages)

    Returns:
        Decorated function with standard error handling

    Example:
        @standard_error_handling("Contract validation processing")
        def process(self, input_state):
            # Just business logic - no try/catch needed
            return result

    Pattern Applied:
        try:
            return original_function(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt, GeneratorExit):
            raise  # Never catch cancellation/exit signals
        except asyncio.CancelledError:
            raise  # Never suppress async cancellation
        except ModelOnexError:
            raise  # Always re-raise ModelOnexError as-is
        except Exception as e:
            raise ModelOnexError(
                f"{operation_name} failed: {str(e)}",
                EnumCoreErrorCode.OPERATION_FAILED
            ) from e

    Note:
        Cancellation and exit signals (SystemExit, KeyboardInterrupt,
        GeneratorExit, asyncio.CancelledError) are NEVER caught. These
        must propagate for proper shutdown and task cancellation semantics.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is to preserve error context
                    raise
                except Exception as e:
                    # boundary-ok: convert generic exceptions to ModelOnexError with proper chaining
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is to preserve error context
                    raise
                except Exception as e:
                    # boundary-ok: convert generic exceptions to ModelOnexError with proper chaining
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return wrapper

    return decorator


def validation_error_handling(
    operation_name: str = "validation",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for validation operations that may throw ValidationError.

    This is a specialized version of standard_error_handling that treats
    ValidationError as a separate case with VALIDATION_ERROR code.

    Args:
        operation_name: Human-readable name for the validation operation

    Returns:
        Decorated function with validation-specific error handling

    Example:
        @validation_error_handling("Contract validation")
        def validate_contract(self, contract_data):
            # Validation logic that may throw ValidationError
            return validation_result

    Note:
        Cancellation and exit signals (SystemExit, KeyboardInterrupt,
        GeneratorExit, asyncio.CancelledError) are NEVER caught. These
        must propagate for proper shutdown and task cancellation semantics.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is
                    raise
                except Exception as e:
                    # boundary-ok: convert exceptions to structured ONEX errors for validation ops
                    # Use robust validation error detection (type check + duck typing)
                    # See _is_validation_error() docstring for detection strategy
                    if _is_validation_error(e):
                        msg = f"{operation_name} failed: {e!s}"
                        raise ModelOnexError(
                            msg,
                            EnumCoreErrorCode.VALIDATION_ERROR,
                            original_error_type=type(e).__name__,
                            operation=operation_name,
                            is_validation_error=True,
                        ) from e
                    # Generic operation failure (non-validation error)
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is
                    raise
                except Exception as e:
                    # boundary-ok: convert exceptions to structured ONEX errors for validation ops
                    # Use robust validation error detection (type check + duck typing)
                    # See _is_validation_error() docstring for detection strategy
                    if _is_validation_error(e):
                        msg = f"{operation_name} failed: {e!s}"
                        raise ModelOnexError(
                            msg,
                            EnumCoreErrorCode.VALIDATION_ERROR,
                            original_error_type=type(e).__name__,
                            operation=operation_name,
                            is_validation_error=True,
                        ) from e
                    # Generic operation failure (non-validation error)
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return wrapper

    return decorator


def io_error_handling(
    operation_name: str = "I/O operation",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for I/O operations (file/network) with appropriate error codes.

    Args:
        operation_name: Human-readable name for the I/O operation

    Returns:
        Decorated function with I/O-specific error handling

    Example:
        @io_error_handling("File reading")
        def read_contract_file(self, file_path):
            # File I/O logic
            return file_content

    Note:
        Cancellation and exit signals (SystemExit, KeyboardInterrupt,
        GeneratorExit, asyncio.CancelledError) are NEVER caught. These
        must propagate for proper shutdown and task cancellation semantics.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is
                    raise
                except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                    # File system errors
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        (
                            EnumCoreErrorCode.FILE_NOT_FOUND
                            if isinstance(e, FileNotFoundError)
                            else EnumCoreErrorCode.FILE_OPERATION_ERROR
                        ),
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                        is_file_error=True,
                    ) from e
                except Exception as e:
                    # boundary-ok: convert generic I/O failures to structured ONEX errors
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return async_wrapper
        else:

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except (GeneratorExit, KeyboardInterrupt, SystemExit):
                    # Never catch cancellation/exit signals - they must propagate
                    raise
                except asyncio.CancelledError:
                    # Never suppress async cancellation - required for proper task cleanup
                    raise
                except ModelOnexError:
                    # Always re-raise ModelOnexError as-is
                    raise
                except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                    # File system errors
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        (
                            EnumCoreErrorCode.FILE_NOT_FOUND
                            if isinstance(e, FileNotFoundError)
                            else EnumCoreErrorCode.FILE_OPERATION_ERROR
                        ),
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                        is_file_error=True,
                    ) from e
                except Exception as e:
                    # boundary-ok: convert generic I/O failures to structured ONEX errors
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.OPERATION_FAILED,
                        original_error_type=type(e).__name__,
                        operation=operation_name,
                    ) from e

            return wrapper

    return decorator
