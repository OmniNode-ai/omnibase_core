from typing import Callable

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
Standard error handling decorators for ONEX framework.

This module provides decorators that eliminate error handling boilerplate
and ensure consistent error patterns across all tools, especially important
for agent-generated tools.
"""

import functools
from collections.abc import Callable as CallableABC
from typing import Any, Callable

from omnibase_core.errors import ModelOnexError
from omnibase_core.errors.error_codes import EnumCoreErrorCode


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
        except ModelOnexError:
            raise  # Always re-raise ModelOnexError as-is
        except Exception as e:
            raise ModelOnexError(
                f"{operation_name} failed: {str(e)}",
                EnumCoreErrorCode.OPERATION_FAILED
            ) from e
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except ModelOnexError:
                # Always re-raise ModelOnexError as-is to preserve error context
                raise
            except Exception as e:
                # Convert generic exceptions to ModelOnexError with proper chaining
                msg = f"{operation_name} failed: {e!s}"
                raise ModelOnexError(
                    msg,
                    EnumCoreErrorCode.OPERATION_FAILED,
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
            except ModelOnexError:
                # Always re-raise ModelOnexError as-is
                raise
            except Exception as e:
                # Check if this is a validation error (duck typing)
                if hasattr(e, "errors") or "validation" in str(e).lower():
                    msg = f"{operation_name} failed: {e!s}"
                    raise ModelOnexError(
                        msg,
                        EnumCoreErrorCode.VALIDATION_ERROR,
                    ) from e
                # Generic operation failure
                msg = f"{operation_name} failed: {e!s}"
                raise ModelOnexError(
                    msg,
                    EnumCoreErrorCode.OPERATION_FAILED,
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
                        else EnumCoreErrorCode.FILESYSTEM_ERROR
                    ),
                ) from e
            except Exception as e:
                # Generic I/O failure
                msg = f"{operation_name} failed: {e!s}"
                raise ModelOnexError(
                    msg,
                    EnumCoreErrorCode.OPERATION_FAILED,
                ) from e

        return wrapper

    return decorator
