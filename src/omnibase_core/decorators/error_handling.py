"""
Standard error handling decorators for ONEX framework.

This module provides decorators that eliminate error handling boilerplate
and ensure consistent error patterns across all tools, especially important
for agent-generated tools.
"""

import functools
from typing import Any, Callable

from omnibase_core.core.core_error_codes import CoreErrorCode
from omnibase_core.exceptions import OnexError


def standard_error_handling(operation_name: str = "operation"):
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
        except OnexError:
            raise  # Always re-raise OnexError as-is
        except Exception as e:
            raise OnexError(
                f"{operation_name} failed: {str(e)}",
                CoreErrorCode.OPERATION_FAILED
            ) from e
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except OnexError:
                # Always re-raise OnexError as-is to preserve error context
                raise
            except Exception as e:
                # Convert generic exceptions to OnexError with proper chaining
                raise OnexError(
                    f"{operation_name} failed: {str(e)}", CoreErrorCode.OPERATION_FAILED
                ) from e

        return wrapper

    return decorator


def validation_error_handling(operation_name: str = "validation"):
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
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except OnexError:
                # Always re-raise OnexError as-is
                raise
            except Exception as e:
                # Check if this is a validation error (duck typing)
                if hasattr(e, "errors") or "validation" in str(e).lower():
                    raise OnexError(
                        f"{operation_name} failed: {str(e)}",
                        CoreErrorCode.VALIDATION_ERROR,
                    ) from e
                else:
                    # Generic operation failure
                    raise OnexError(
                        f"{operation_name} failed: {str(e)}",
                        CoreErrorCode.OPERATION_FAILED,
                    ) from e

        return wrapper

    return decorator


def io_error_handling(operation_name: str = "I/O operation"):
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
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except OnexError:
                # Always re-raise OnexError as-is
                raise
            except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
                # File system errors
                raise OnexError(
                    f"{operation_name} failed: {str(e)}",
                    (
                        CoreErrorCode.FILE_NOT_FOUND
                        if isinstance(e, FileNotFoundError)
                        else CoreErrorCode.FILESYSTEM_ERROR
                    ),
                ) from e
            except Exception as e:
                # Generic I/O failure
                raise OnexError(
                    f"{operation_name} failed: {str(e)}", CoreErrorCode.OPERATION_FAILED
                ) from e

        return wrapper

    return decorator
