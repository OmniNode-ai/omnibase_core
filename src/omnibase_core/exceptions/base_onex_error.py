#!/usr/bin/env python3
"""
ONEX Error System

Standardized error handling for the ONEX framework.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnibase_core.core.core_error_codes import CoreErrorCode


class OnexError(Exception):
    """
    Standard ONEX error with error code and details.

    All exceptions in ONEX must be converted to OnexError with proper error codes.
    """

    def __init__(
        self,
        code: "CoreErrorCode",
        message: str,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ):
        """
        Initialize ONEX error.

        Args:
            code: Error code from CoreErrorCode enum
            message: Human-readable error message
            details: Additional error details
            cause: Original exception that caused this error
        """
        self.code = code
        self.message = message
        self.details = details or {}
        self.cause = cause

        # Build full message
        full_message = f"[{code.value}] {message}"
        if details:
            full_message += f" | Details: {details}"

        super().__init__(full_message)

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for serialization."""
        # Custom error serialization format
        result = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }

        if self.cause:
            result["cause"] = str(self.cause)

        return result
