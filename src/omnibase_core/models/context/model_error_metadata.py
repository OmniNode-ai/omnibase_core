"""
Error metadata model for structured error metadata.

This module provides ModelErrorMetadata, a typed model for error-related
metadata that supports correlation, retry logic, and categorization across
the ONEX system.

Note:
    This model was renamed from ModelErrorContext to ModelErrorMetadata
    to avoid naming conflict with omnibase_core.models.common.model_error_context
    which provides error location context (file, line, function, etc.).

Error Code Format:
    Error codes must follow the CATEGORY_NNN pattern (e.g., AUTH_001,
    VALIDATION_123, SYSTEM_01). The format is validated using the regex
    pattern: ^[A-Z][A-Z0-9_]*_\\d{1,4}$

    For complete error code standards including valid/invalid examples,
    standard categories, and best practices, see:
    docs/conventions/ERROR_CODE_STANDARDS.md

Thread Safety:
    ModelErrorMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.constants.constants_error: Centralized error code pattern
      (ERROR_CODE_PATTERN). This is the single source of truth for the
      CATEGORY_NNN format validation.
    - docs/conventions/ERROR_CODE_STANDARDS.md: Complete error code format specification
    - docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md: Error handling patterns
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_audit_metadata: Audit trail metadata
    - omnibase_core.models.common.model_error_context: Error location context
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN

__all__ = [
    "ModelErrorMetadata",
    # Error code pattern re-exported from centralized location
    "ERROR_CODE_PATTERN",
    # Error category constants
    "CATEGORY_VALIDATION",
    "CATEGORY_AUTH",
    "CATEGORY_SYSTEM",
    "CATEGORY_NETWORK",
    # Category groupings
    "CLIENT_ERROR_CATEGORIES",
    "SERVER_ERROR_CATEGORIES",
]

# -----------------------------------------------------------------------------
# Error Code Pattern (Centralized)
# -----------------------------------------------------------------------------
# The ERROR_CODE_PATTERN is now imported from omnibase_core.constants.constants_error
# which provides the single source of truth for error code validation.
#
# Pattern: ^[A-Z][A-Z0-9_]*_\d{1,4}$
# - Valid: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001, SYSTEM_01
# - Invalid: E001 (lint-style, no underscore), auth_001 (lowercase)
#
# For direct validation (not in Pydantic models), prefer using:
#   from omnibase_core.validation.validators import validate_error_code

# -----------------------------------------------------------------------------
# Error Category Constants
# -----------------------------------------------------------------------------
# These constants define the standard error categories used for classification.
# Using constants ensures consistency and makes refactoring easier.

# Client-side error categories (caused by invalid input or auth issues)
CATEGORY_VALIDATION = "validation"
CATEGORY_AUTH = "auth"

# Server-side error categories (caused by internal failures or network issues)
CATEGORY_SYSTEM = "system"
CATEGORY_NETWORK = "network"

# Tuple collections for category classification
CLIENT_ERROR_CATEGORIES: tuple[str, ...] = (CATEGORY_VALIDATION, CATEGORY_AUTH)
SERVER_ERROR_CATEGORIES: tuple[str, ...] = (CATEGORY_SYSTEM, CATEGORY_NETWORK)


class ModelErrorMetadata(BaseModel):
    """Metadata model for structured error metadata.

    Provides consistent error tracking across the system with support for
    correlation, retry logic, and categorization. All fields are optional
    as error metadata may be partially populated depending on the error
    source and context.

    Note:
        This model was renamed from ModelErrorContext to avoid naming
        conflict with omnibase_core.models.common.model_error_context.ModelErrorContext
        which provides error location context (file path, line number, etc.).

    Attributes:
        error_code: Structured error code following CATEGORY_NNN format
            (e.g., "AUTH_001", "VALIDATION_123"). Used for programmatic
            error handling and documentation references.
        error_category: Error category for broad classification. Use the
            module-level constants (CATEGORY_VALIDATION, CATEGORY_AUTH,
            CATEGORY_SYSTEM, CATEGORY_NETWORK) for standard values.
            Used for error routing and handling strategies.
        correlation_id: Request correlation ID for distributed tracing.
            Links related errors across service boundaries.
        stack_trace_id: Reference to stored stack trace. Used when full
            stack traces are stored separately for security/size reasons.
        retry_count: Number of retry attempts made for this operation.
            Must be >= 0 if provided. None indicates retries are not
            applicable (e.g., operation doesn't support retries); 0
            indicates retries are applicable but none attempted yet.
            See should_retry() for retry decision logic.
        is_retryable: Whether the error can be retried. Used by retry
            logic to determine if automatic retry should be attempted.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelErrorMetadata
        >>>
        >>> error_meta = ModelErrorMetadata(
        ...     error_code="AUTH_001",
        ...     error_category="auth",
        ...     correlation_id="req_abc123",
        ...     retry_count=0,
        ...     is_retryable=True,
        ... )
        >>> error_meta.should_retry(max_retries=3)
        True
        >>> error_meta.is_client_error()
        True

    See Also:
        - :mod:`omnibase_core.constants.constants_error`: Centralized error code
          pattern (ERROR_CODE_PATTERN) used for validation. This is the single
          source of truth for the CATEGORY_NNN format.
        - :doc:`docs/conventions/ERROR_CODE_STANDARDS.md`: Complete error code
          format specification, valid/invalid examples, and best practices.
        - :doc:`docs/conventions/ERROR_HANDLING_BEST_PRACTICES.md`: Comprehensive
          error handling patterns and recovery strategies.
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
    stack_trace_id: UUID | None = Field(
        default=None,
        description="Reference to stored stack trace",
    )
    retry_count: int | None = Field(
        default=None,
        description=(
            "Number of retry attempts made. None indicates retries are not "
            "applicable to this error context (e.g., the operation does not "
            "support retries or retry tracking is disabled); 0 indicates that "
            "retries are applicable but no retry attempts have been made yet."
        ),
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
            ValueError: If retry_count is not an integer or is negative.
        """
        if value is None:
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"retry_count must be an integer, got {type(value).__name__}"
            )
        if value < 0:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"retry_count must be >= 0, got {value}")
        return value

    @field_validator("error_code", mode="before")
    @classmethod
    def validate_error_code_format(cls, value: str | None) -> str | None:
        """Validate error_code follows CATEGORY_NNN pattern if provided.

        The pattern is optional but recommended for consistency. Accepts
        formats like AUTH_001, VALIDATION_123, SYSTEM_01.

        Uses the module-level ERROR_CODE_PATTERN which is compiled once
        at import time for performance (regex caching).

        Note:
            For direct validation outside Pydantic models, prefer using
            validate_error_code() from validator_common instead.
            The pattern is intentionally duplicated here to avoid circular
            imports - see module-level comments for details.

        Args:
            value: The error code string or None.

        Returns:
            The validated error code string unchanged, or None.

        Raises:
            ValueError: If the value is not a string or doesn't match the expected pattern.
        """
        if value is None:
            return None
        if not isinstance(value, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"error_code must be a string, got {type(value).__name__}")
        if not value:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError("Error code cannot be empty")
        if not ERROR_CODE_PATTERN.match(value):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid error_code format '{value}': expected CATEGORY_NNN "
                f"pattern (e.g., AUTH_001, VALIDATION_123). "
                f"For lint-style short codes (W001, E001), use checker_workflow_linter module."
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
            >>> ctx = ModelErrorMetadata(is_retryable=True, retry_count=1)
            >>> ctx.should_retry(max_retries=3)
            True
            >>> ctx = ModelErrorMetadata(is_retryable=True, retry_count=3)
            >>> ctx.should_retry(max_retries=3)
            False
        """
        if not self.is_retryable:
            return False
        if self.retry_count is None:
            return False
        return self.retry_count < max_retries

    @classmethod
    def get_client_error_categories(cls) -> tuple[str, ...]:
        """Get the tuple of error categories considered client errors.

        Override this method in subclasses to extend or customize
        the client error category classification.

        Returns:
            Tuple of category strings that are considered client errors.
            Default: ("validation", "auth")

        Example:
            Extending client categories in a subclass::

                class MyErrorMetadata(ModelErrorMetadata):
                    @classmethod
                    def get_client_error_categories(cls) -> tuple[str, ...]:
                        return super().get_client_error_categories() + ("rate_limit",)
        """
        return CLIENT_ERROR_CATEGORIES

    @classmethod
    def get_server_error_categories(cls) -> tuple[str, ...]:
        """Get the tuple of error categories considered server errors.

        Override this method in subclasses to extend or customize
        the server error category classification.

        Returns:
            Tuple of category strings that are considered server errors.
            Default: ("system", "network")

        Example:
            Extending server categories in a subclass::

                class MyErrorMetadata(ModelErrorMetadata):
                    @classmethod
                    def get_server_error_categories(cls) -> tuple[str, ...]:
                        return super().get_server_error_categories() + ("database",)
        """
        return SERVER_ERROR_CATEGORIES

    def is_client_error(self) -> bool:
        """Check if this is a client-side error.

        Client errors are typically caused by invalid input or
        authentication/authorization issues. Uses get_client_error_categories()
        for classification, which can be overridden in subclasses.

        Returns:
            True if error_category is in the client error categories
            (default: "validation" or "auth"), False otherwise
            (including when error_category is None).

        Note:
            To extend client error categories in a subclass, override
            the get_client_error_categories() class method.

        Example:
            >>> ctx = ModelErrorMetadata(error_category="validation")
            >>> ctx.is_client_error()
            True
            >>> ctx = ModelErrorMetadata(error_category="system")
            >>> ctx.is_client_error()
            False
        """
        return self.error_category in self.get_client_error_categories()

    def is_server_error(self) -> bool:
        """Check if this is a server-side error.

        Server errors are typically caused by internal system failures
        or network issues. Uses get_server_error_categories() for
        classification, which can be overridden in subclasses.

        Returns:
            True if error_category is in the server error categories
            (default: "system" or "network"), False otherwise
            (including when error_category is None).

        Note:
            To extend server error categories in a subclass, override
            the get_server_error_categories() class method.

        Example:
            >>> ctx = ModelErrorMetadata(error_category="system")
            >>> ctx.is_server_error()
            True
            >>> ctx = ModelErrorMetadata(error_category="auth")
            >>> ctx.is_server_error()
            False
        """
        return self.error_category in self.get_server_error_categories()
