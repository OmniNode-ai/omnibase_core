#!/usr/bin/env python3
"""
ONEX Error System

Standardized error handling for the ONEX framework.
"""

from enum import Enum
from typing import Any


class CoreErrorCode(str, Enum):
    """Core error codes for ONEX system."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    OPERATION_FAILED = "OPERATION_FAILED"
    NOT_FOUND = "NOT_FOUND"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class OnexError(Exception):
    """
    Standard ONEX error with error code and details.

    All exceptions in ONEX must be converted to OnexError with proper error codes.
    """

    def __init__(
        self,
        code: CoreErrorCode,
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
        result = {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
        }

        if self.cause:
            result["cause"] = str(self.cause)

        return result
