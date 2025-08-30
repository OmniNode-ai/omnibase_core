"""
Error utilities for consistent error handling in ONEX system.
"""

from typing import Optional

from omnibase_core.core.core_errors import CoreErrorCode, OnexError


def handle_exception(
    e: Exception,
    source: str,
    message: Optional[str] = None,
    error_code: CoreErrorCode = CoreErrorCode.EXECUTION_ERROR,
    metadata: Optional[dict] = None,
) -> OnexError:
    """
    Convert any exception to OnexError for consistent handling.

    Args:
        e: The exception to handle
        source: The source component
        message: Optional custom message
        error_code: The error code to use
        metadata: Optional metadata

    Returns:
        OnexError instance
    """
    # If already OnexError, return as-is
    if isinstance(e, OnexError):
        return e

    # Build error message
    error_message = message or f"{type(e).__name__}: {str(e)}"

    # Build metadata
    error_metadata = {"original_error": type(e).__name__, "original_message": str(e)}
    if metadata:
        error_metadata.update(metadata)

    return OnexError(
        error_code=error_code,
        message=error_message,
        source=source,
        metadata=error_metadata,
    )
