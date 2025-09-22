#!/usr/bin/env python3
"""
ONEX Error System

Standardized error handling for the ONEX framework.
"""

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext


class OnexError(Exception):
    """
    Standard ONEX error with error code and details.

    All exceptions in ONEX must be converted to OnexError with proper error codes.
    """

    def __init__(
        self,
        code: EnumCoreErrorCode,
        message: str,
        details: ModelErrorContext | None = None,
        cause: Exception | None = None,
    ):
        """
        Initialize ONEX error.

        Args:
            code: Error code from EnumCoreErrorCode enum
            message: Human-readable error message
            details: Additional error details as structured context
            cause: Original exception that caused this error
        """
        self.code = code
        self.message = message
        self.details = details or ModelErrorContext.with_context({})
        self.cause = cause

        # Build full message
        full_message = f"[{code.value}] {message}"
        if details and details.additional_context:
            context_summary = ", ".join(
                f"{k}={v.to_value()}" for k, v in details.additional_context.items()
            )
            full_message += f" | Context: {context_summary}"

        super().__init__(full_message)
