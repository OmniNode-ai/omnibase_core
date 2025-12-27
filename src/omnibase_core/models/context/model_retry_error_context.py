# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Error context model for structured error tracking.

This module provides ModelErrorContext, a typed context model for tracking
error information including error codes, categories, correlation IDs,
retry state, and helper methods for error classification.

Thread Safety:
    ModelErrorContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelRetryContext: For retry-specific metadata
    - ModelOperationalErrorContext: For operational error tracking
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Pattern for error codes: CATEGORY_NNN format (e.g., AUTH_001, VALIDATION_123)
#
# IMPORTANT: This pattern is defined here AND in model_operational_error_context.py.
# Both patterns MUST be kept in sync. See that module for detailed documentation
# on the pattern format and rationale.
#
# The pattern supports multi-character category prefixes with underscores:
# - Valid: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001, SYSTEM_01
# - Invalid: E001 (lint-style, no underscore), auth_001 (lowercase)
ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_\d{1,4}$")


class ModelErrorContext(BaseModel):
    """Typed context for error tracking metadata.

    This model provides structured fields for tracking error information
    including codes, categories, correlation IDs, and retry state.

    Use Cases:
        - Error tracking and classification
        - Retry logic decision making
        - Client vs server error categorization
        - Correlation across distributed systems

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        error_code: Error code in UPPERCASE_CATEGORY_123 format (e.g., "AUTH_001").
        error_category: Category like "auth", "validation", "system", "network".
        correlation_id: Request correlation ID for distributed tracing.
        stack_trace_ref: Stack trace reference for debugging.
        retry_count: Number of retry attempts (must be >= 0).
        is_retryable: Whether the error can be retried.

    Example:
        Create error context with all fields::

            from omnibase_core.models.context import ModelErrorContext

            context = ModelErrorContext(
                error_code="AUTH_001",
                error_category="auth",
                correlation_id="req_abc123",
                retry_count=2,
                is_retryable=True,
            )

        Check if should retry::

            if context.should_retry(max_retries=3):
                # Perform retry
                pass

        Classify error type::

            if context.is_client_error():
                # Handle client error (4xx equivalent)
                pass
            elif context.is_server_error():
                # Handle server error (5xx equivalent)
                pass

    See Also:
        - ModelRetryContext: For retry-specific metadata
        - ModelOperationalErrorContext: For operational error tracking
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    error_code: str | None = Field(
        default=None,
        description="Error code in UPPERCASE_CATEGORY_123 format (e.g., AUTH_001)",
    )
    error_category: str | None = Field(
        default=None,
        description="Error category (e.g., auth, validation, system, network)",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for distributed tracing",
    )
    stack_trace_ref: str | None = Field(
        default=None,
        description="Stack trace reference for debugging",
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts (must be >= 0)",
    )
    is_retryable: bool | None = Field(
        default=None,
        description="Whether the error can be retried",
    )

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, v: str | None) -> str | None:
        """Validate error_code matches expected pattern.

        Args:
            v: The error code value to validate.

        Returns:
            The validated error code or None.

        Raises:
            ValueError: If the error code doesn't match the expected pattern.
        """
        if v is None:
            return v
        if not ERROR_CODE_PATTERN.match(v):
            raise ValueError(
                f"error_code must match pattern UPPERCASE_CATEGORY_123 "
                f"(e.g., AUTH_001, RATE_LIMIT_001), got: {v!r}"
            )
        return v

    @field_validator("retry_count")
    @classmethod
    def validate_retry_count(cls, v: int | None) -> int | None:
        """Validate retry_count is non-negative.

        Args:
            v: The retry count value to validate.

        Returns:
            The validated retry count or None.

        Raises:
            ValueError: If retry_count is negative.
        """
        if v is not None and v < 0:
            raise ValueError(f"retry_count must be >= 0, got: {v}")
        return v

    def should_retry(self, max_retries: int = 3) -> bool:
        """Determine if the error should be retried.

        Returns True if all of the following conditions are met:
        - is_retryable is True
        - retry_count is not None
        - retry_count < max_retries

        Args:
            max_retries: Maximum number of retry attempts allowed. Defaults to 3.

        Returns:
            True if the error should be retried, False otherwise.
        """
        if self.is_retryable is not True:
            return False
        if self.retry_count is None:
            return False
        return self.retry_count < max_retries

    def is_client_error(self) -> bool:
        """Check if this is a client-side error.

        Client errors are categorized as "validation" or "auth" errors,
        analogous to HTTP 4xx status codes.

        Returns:
            True if error_category is "validation" or "auth", False otherwise.
        """
        return self.error_category in ("validation", "auth")

    def is_server_error(self) -> bool:
        """Check if this is a server-side error.

        Server errors are categorized as "system" or "network" errors,
        analogous to HTTP 5xx status codes.

        Returns:
            True if error_category is "system" or "network", False otherwise.
        """
        return self.error_category in ("system", "network")
