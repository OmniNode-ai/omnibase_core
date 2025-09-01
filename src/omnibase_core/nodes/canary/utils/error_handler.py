#!/usr/bin/env python3
"""
Enhanced error handling for canary nodes with security considerations.

Provides secure error handling that prevents information disclosure while
maintaining debugging capabilities in appropriate environments.
"""

import logging
import traceback
import uuid
from typing import Any, Dict, Optional

from omnibase_core.nodes.canary.config.canary_config import get_canary_config


class SecureErrorHandler:
    """Secure error handling with information disclosure protection."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.config = get_canary_config()
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None,
        operation_name: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Handle error with appropriate logging and sanitized user response.

        Args:
            error: The exception that occurred
            context: Context information about the operation
            correlation_id: Request correlation ID for tracing
            operation_name: Name of the operation that failed

        Returns:
            Sanitized error information safe for client consumption
        """

        # Generate unique error ID for tracking
        error_id = str(uuid.uuid4())[:8]

        # Create detailed error info for logging
        detailed_error = {
            "error_id": error_id,
            "operation": operation_name,
            "correlation_id": correlation_id or "unknown",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": self._sanitize_context(context),
        }

        # Add stack trace if not in production or configured to sanitize
        if not self.config.security.sanitize_stack_traces:
            detailed_error["stack_trace"] = traceback.format_exc()
        else:
            # Only log stack trace, don't include in response
            self.logger.error(
                f"Error {error_id} stack trace: {traceback.format_exc()}",
                extra={"correlation_id": correlation_id},
            )

        # Log the detailed error
        self.logger.error(
            f"Operation failed: {operation_name}",
            extra={**detailed_error, "correlation_id": correlation_id},
        )

        # Return sanitized error for client
        sanitized_error = {
            "error_id": error_id,
            "message": self._get_safe_error_message(error),
            "operation": operation_name,
            "timestamp": context.get("timestamp"),
        }

        # Include correlation ID if present for tracing
        if correlation_id:
            sanitized_error["correlation_id"] = correlation_id

        return sanitized_error

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from context."""

        sanitized = {}
        sensitive_keys = {
            "password",
            "token",
            "secret",
            "key",
            "auth",
            "credential",
            "api_key",
            "access_token",
            "refresh_token",
            "jwt",
            "session",
        }

        for key, value in context.items():
            key_lower = key.lower()

            # Skip sensitive keys
            if any(sensitive_key in key_lower for sensitive_key in sensitive_keys):
                sanitized[key] = "[REDACTED]"
            # Truncate very long values
            elif (
                isinstance(value, str)
                and len(value) > self.config.security.max_error_detail_length
            ):
                sanitized[key] = (
                    value[: self.config.security.max_error_detail_length]
                    + "...[TRUNCATED]"
                )
            else:
                sanitized[key] = value

        return sanitized

    def _get_safe_error_message(self, error: Exception) -> str:
        """Get a safe error message that doesn't leak sensitive information."""

        error_type = type(error).__name__

        # Map common error types to safe user messages
        safe_messages = {
            "ConnectionError": "Service temporarily unavailable",
            "TimeoutError": "Operation timed out",
            "PermissionError": "Access denied",
            "FileNotFoundError": "Resource not found",
            "ValueError": "Invalid input provided",
            "KeyError": "Required parameter missing",
            "TypeError": "Invalid data type provided",
            "AttributeError": "Invalid operation attempted",
        }

        # Use safe message if available, otherwise generic message
        safe_message = safe_messages.get(error_type, "Operation failed")

        # In non-production or when configured, include original message
        if (
            not self.config.security.sanitize_stack_traces
            or self.config.security.log_sensitive_data
        ):
            original_message = str(error)
            if (
                original_message
                and len(original_message)
                <= self.config.security.max_error_detail_length
            ):
                return f"{safe_message}: {original_message}"

        return safe_message

    def validate_correlation_id(self, correlation_id: Optional[str]) -> bool:
        """Validate correlation ID format if validation is enabled."""

        if not self.config.security.correlation_id_validation:
            return True

        if not correlation_id:
            return False

        # Basic validation - should be UUID-like or alphanumeric
        if not correlation_id.replace("-", "").replace("_", "").isalnum():
            return False

        # Length check
        if len(correlation_id) < 8 or len(correlation_id) > 128:
            return False

        return True

    def create_operation_context(
        self,
        operation_name: str,
        input_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create standardized operation context for error handling."""

        from datetime import datetime

        context = {
            "operation": operation_name,
            "timestamp": datetime.utcnow().isoformat(),
            "input_keys": list(input_data.keys()) if input_data else [],
        }

        if correlation_id and self.validate_correlation_id(correlation_id):
            context["correlation_id"] = correlation_id

        # Add non-sensitive input data for debugging
        if self.config.security.log_sensitive_data:
            context["input_data"] = input_data
        else:
            # Only log data types and sizes, not actual values
            context["input_data_info"] = {
                key: {
                    "type": type(value).__name__,
                    "size": len(str(value)) if value is not None else 0,
                }
                for key, value in (input_data or {}).items()
            }

        return context


# Global error handler instance
_error_handler_instance: SecureErrorHandler | None = None


def get_error_handler(logger: Optional[logging.Logger] = None) -> SecureErrorHandler:
    """Get the global error handler instance."""
    global _error_handler_instance
    if _error_handler_instance is None:
        _error_handler_instance = SecureErrorHandler(logger)
    return _error_handler_instance
