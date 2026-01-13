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


def _is_pydantic_validation_error_structure(errors_result: object) -> bool:
    """Check if errors() result matches Pydantic ValidationError structure.

    Pydantic v2 ValidationError.errors() returns a list of dicts, each with
    at least 'loc', 'msg', and 'type' keys. This function validates that
    structure to avoid false positives from other exceptions that happen
    to have an errors() method.

    Args:
        errors_result: The result of calling exc.errors()

    Returns:
        True if the structure matches Pydantic ValidationError format.

    Limitations:
        - Only checks first error to avoid performance overhead
        - Does not validate types of dict values
        - May still match non-Pydantic libraries that use same structure
    """
    if not isinstance(errors_result, list):
        return False
    if not errors_result:
        # Empty errors list is still valid Pydantic structure
        return True
    # Check first error has expected Pydantic keys
    first_error = errors_result[0]
    if not isinstance(first_error, dict):
        return False
    # Pydantic v2 errors have 'loc', 'msg', 'type' keys (required)
    # and often 'input' and 'url' keys (optional but common in v2)
    required_keys = {"loc", "msg", "type"}
    return required_keys.issubset(first_error.keys())


def _has_pydantic_error_count_method(exc: Exception) -> bool:
    """Check if exception has Pydantic's error_count() method.

    Pydantic v2 ValidationError has an error_count() method that returns
    the number of validation errors. This is a more reliable indicator
    than just checking for errors() since it's Pydantic-specific.

    Args:
        exc: The exception to check.

    Returns:
        True if exception has a callable error_count() returning an int.
    """
    error_count_attr = getattr(exc, "error_count", None)
    if not callable(error_count_attr):
        return False
    try:
        result = error_count_attr()
        return isinstance(result, int)
    except Exception:
        # fallback-ok: error_count() call failed, not Pydantic-like
        return False


# Denylist of class name patterns that contain "validation" but are NOT
# validation errors. These are typically timeout/cancellation/infrastructure
# errors that happen to be related to a validation process.
# Pattern: exception class name suffix (case-insensitive matching)
_VALIDATION_NAME_FALSE_POSITIVES = frozenset(
    {
        "validationtimeouterror",
        "validationtimeout",
        "validationcancellederror",
        "validationcancelled",
        "validationconnectionerror",
        "validationnetworkerror",
        "validationinitializationerror",
        "validationsetuperror",
        "validationconfigurationerror",
    }
)


def _is_validation_error(exc: Exception) -> bool:
    """Determine if an exception represents a validation error.

    This function uses a multi-tier detection strategy, ordered from most
    reliable to least reliable:

    1. Type checking against VALIDATION_ERRORS tuple (TypeError, ValidationError,
       ValueError) - most reliable, covers standard Python and Pydantic errors.
    2. Duck typing for Pydantic ValidationError: checks for BOTH `errors()` method
       with Pydantic structure AND `error_count()` method returning int. Having
       both methods is a strong signal of Pydantic-style validation errors.
    3. Exception class name check: if class name contains "Validation" or
       "validation" AND is not in the denylist of known false positives
       (e.g., ValidationTimeoutError), treat as validation error.

    Args:
        exc: The exception to check.

    Returns:
        True if the exception appears to be a validation error, False otherwise.

    Known Limitations:
        - Tier 2 duck typing may still match non-Pydantic validation libraries
          that happen to use the same error structure (loc/msg/type dicts with
          error_count method). This is considered acceptable as they are likely
          validation errors.
        - Tier 3 denylist may need to be extended for new false positive patterns.
        - Does not detect validation errors from libraries that use different
          error structures without "validation" in their class name.

    Duck-typing strategy (Tier 2):
        Pydantic v2 ValidationError has these distinguishing characteristics:
        - `errors()` method returning list of dicts with 'loc', 'msg', 'type' keys
        - `error_count()` method returning int
        - `json()` method for serialization
        - `title` attribute with model name

        We require EITHER:
        (a) errors() with valid Pydantic structure, OR
        (b) error_count() returning int

        Having either is sufficient evidence of a validation-style error.

    Class name heuristic (Tier 3):
        The denylist (_VALIDATION_NAME_FALSE_POSITIVES) excludes exceptions where
        "validation" is a context modifier rather than indicating the error type:
        - ValidationTimeoutError: timeout during validation (infrastructure error)
        - ValidationCancelledError: validation was cancelled (control flow)
        - ValidationConnectionError: connection failed during validation (I/O error)
    """
    # Tier 1: Direct type check against known validation error types
    # This is the most reliable check and covers:
    # - TypeError: type coercion failures
    # - ValidationError: Pydantic validation failures
    # - ValueError: value constraint violations
    if isinstance(exc, VALIDATION_ERRORS):
        return True

    # Tier 2: Duck typing for Pydantic-style ValidationError
    # We check for Pydantic's characteristic methods:
    # - errors() returning list of dicts with 'loc', 'msg', 'type' keys
    # - error_count() returning an integer
    # Either method is sufficient evidence of a validation-style error.

    # Check for error_count() method (Pydantic-specific, more reliable)
    if _has_pydantic_error_count_method(exc):
        return True

    # Check for errors() method with Pydantic structure
    errors_attr = getattr(exc, "errors", None)
    if callable(errors_attr):
        try:
            errors_result = errors_attr()
            if _is_pydantic_validation_error_structure(errors_result):
                return True
        except Exception:
            # fallback-ok: errors() call failed, continue to next tier
            pass

    # Tier 3: Exception class name heuristic with denylist
    # Check if exception class name indicates validation error, excluding
    # known false positives where "validation" is a context modifier.
    exc_class_name = type(exc).__name__
    exc_class_name_lower = exc_class_name.lower()

    if "validation" in exc_class_name_lower:
        # Check against denylist of known false positives
        # Match against the full lowercased class name
        if exc_class_name_lower not in _VALIDATION_NAME_FALSE_POSITIVES:
            return True
        # If in denylist, this is NOT a validation error
        # (e.g., ValidationTimeoutError is a timeout, not a validation error)

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
        except (GeneratorExit, KeyboardInterrupt, SystemExit):
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
