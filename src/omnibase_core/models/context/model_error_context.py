# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Error context model for structured error metadata.

This module provides ModelErrorContext, a typed model for error-related
metadata that supports correlation, retry logic, and categorization across
the ONEX system.

Error Code Format:
    Error codes must follow the CATEGORY_NNN pattern (e.g., AUTH_001,
    VALIDATION_123, SYSTEM_01). The format is validated using the regex
    pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$

    For complete error code standards including valid/invalid examples,
    standard categories, and best practices, see:
    docs/conventions/ERROR_CODE_STANDARDS.md

Thread Safety:
    ModelErrorContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - docs/conventions/ERROR_CODE_STANDARDS.md: Complete error code format specification
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_audit_metadata: Audit trail metadata
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelErrorContext"]

# Pattern for error codes: CATEGORY_NNN (e.g., AUTH_001, VALIDATION_123)
ERROR_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*_\d{1,4}$")


class ModelErrorContext(BaseModel):
    """Context model for structured error metadata.

    Provides consistent error tracking across the system with support for
    correlation, retry logic, and categorization. All fields are optional
    as error metadata may be partially populated depending on the error
    source and context.

    Attributes:
        error_code: Structured error code following CATEGORY_NNN format
            (e.g., "AUTH_001", "VALIDATION_123"). Used for programmatic
            error handling and documentation references.
        error_category: Error category for broad classification. Common
            values: "validation", "auth", "system", "network". Used for
            error routing and handling strategies.
        correlation_id: Request correlation ID for distributed tracing.
            Links related errors across service boundaries.
        stack_trace_id: Reference to stored stack trace. Used when full
            stack traces are stored separately for security/size reasons.
        retry_count: Number of retry attempts made for this operation.
            Must be >= 0 if provided.
        is_retryable: Whether the error can be retried. Used by retry
            logic to determine if automatic retry should be attempted.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelErrorContext
        >>>
        >>> error_ctx = ModelErrorContext(
        ...     error_code="AUTH_001",
        ...     error_category="auth",
        ...     correlation_id="req_abc123",
        ...     retry_count=0,
        ...     is_retryable=True,
        ... )
        >>> error_ctx.should_retry(max_retries=3)
        True
        >>> error_ctx.is_client_error()
        True
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    error_code: str | None = Field(
        default=None,
        description="Structured error code (e.g., AUTH_001, VALIDATION_123)",
    )
    error_category: str | None = Field(
        default=None,
        description="Error category (validation, auth, system, network)",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing",
    )
    stack_trace_id: str | None = Field(
        default=None,
        description="Reference to stored stack trace",
    )
    retry_count: int | None = Field(
        default=None,
        description="Number of retry attempts made",
    )
    is_retryable: bool | None = Field(
        default=None,
        description="Whether the error can be retried",
    )

    @field_validator("retry_count", mode="before")
    @classmethod
    def validate_retry_count_non_negative(cls, value: int | None) -> int | None:
        """Validate that retry_count is non-negative if provided.

        Args:
            value: The retry count value or None.

        Returns:
            The validated retry count unchanged, or None.

        Raises:
            ValueError: If retry_count is negative.
        """
        if value is not None and value < 0:
            raise ValueError(
                f"retry_count must be >= 0, got {value}"
            )
        return value

    @field_validator("error_code", mode="before")
    @classmethod
    def validate_error_code_format(cls, value: str | None) -> str | None:
        """Validate error_code follows CATEGORY_NNN pattern if provided.

        The pattern is optional but recommended for consistency. Accepts
        formats like AUTH_001, VALIDATION_123, SYSTEM_01.

        Args:
            value: The error code string or None.

        Returns:
            The validated error code string unchanged, or None.

        Raises:
            ValueError: If the error code doesn't match the expected pattern.
        """
        if value is None:
            return None
        if not ERROR_CODE_PATTERN.match(value):
            raise ValueError(
                f"Invalid error_code format '{value}': expected CATEGORY_NNN "
                f"pattern (e.g., AUTH_001, VALIDATION_123)"
            )
        return value

    def should_retry(self, max_retries: int = 3) -> bool:
        """Determine if the operation should be retried.

        Returns True if the error is marked as retryable and the retry
        count is below the maximum threshold.

        Args:
            max_retries: Maximum number of retry attempts allowed.
                Defaults to 3.

        Returns:
            True if the operation should be retried, False otherwise.
            Returns False if is_retryable is None or False, or if
            retry_count is None or >= max_retries.

        Example:
            >>> ctx = ModelErrorContext(is_retryable=True, retry_count=1)
            >>> ctx.should_retry(max_retries=3)
            True
            >>> ctx = ModelErrorContext(is_retryable=True, retry_count=3)
            >>> ctx.should_retry(max_retries=3)
            False
        """
        if not self.is_retryable:
            return False
        if self.retry_count is None:
            return False
        return self.retry_count < max_retries

    def is_client_error(self) -> bool:
        """Check if this is a client-side error.

        Client errors are typically caused by invalid input or
        authentication/authorization issues.

        Returns:
            True if error_category is "validation" or "auth",
            False otherwise (including when error_category is None).

        Example:
            >>> ctx = ModelErrorContext(error_category="validation")
            >>> ctx.is_client_error()
            True
            >>> ctx = ModelErrorContext(error_category="system")
            >>> ctx.is_client_error()
            False
        """
        return self.error_category in ("validation", "auth")

    def is_server_error(self) -> bool:
        """Check if this is a server-side error.

        Server errors are typically caused by internal system failures
        or network issues.

        Returns:
            True if error_category is "system" or "network",
            False otherwise (including when error_category is None).

        Example:
            >>> ctx = ModelErrorContext(error_category="system")
            >>> ctx.is_server_error()
            True
            >>> ctx = ModelErrorContext(error_category="auth")
            >>> ctx.is_server_error()
            False
        """
        return self.error_category in ("system", "network")
