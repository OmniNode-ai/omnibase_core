"""Error details model to replace Dict[str, Any] usage.

This module provides the ModelErrorDetails class, a typed Pydantic model that
replaces untyped dict[str, Any] for error context in ONEX error handling.

Thread Safety:
    ModelErrorDetails instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelOnexError: Primary error class that uses ModelErrorDetails
    - ModelSchemaValue: Type-safe value container for context_data
    - EnumCoreErrorCode: Standard error codes for error_code field

"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.context import (
    ModelOperationalContext,
    ModelResourceContext,
    ModelRetryContext,
    ModelTraceContext,
    ModelUserContext,
    ModelValidationContext,
)

# Type variable for generic context data
# Bound to BaseModel to ensure type safety for typed context models
TContext = TypeVar("TContext", bound=BaseModel)

# Type alias for common error context types
# This union covers the most frequently used context models in error handling
ErrorContext = (
    ModelTraceContext
    | ModelOperationalContext
    | ModelRetryContext
    | ModelResourceContext
    | ModelUserContext
    | ModelValidationContext
    | dict[str, ModelSchemaValue]
)

__all__ = [
    "ModelErrorDetails",
    "TContext",
    "ErrorContext",
]


class ModelErrorDetails(BaseModel, Generic[TContext]):
    """Structured error details with typed fields for ONEX error handling.

    This model replaces dict[str, Any] usage for error_details fields, providing:

    - **Type safety** through Pydantic validation
    - **Consistent error structure** across the codebase
    - **Support for nested errors** via inner_errors field
    - **Recovery information** (retry_after_seconds, recovery_suggestions)
    - **Correlation tracking** (request_id, session_id, user_id)
    - **Generic context data** via TContext type parameter

    Generic Parameters:
        TContext: The type of context data. When unparameterized, defaults to
            dict[str, ModelSchemaValue]. Can be specialized to typed context
            models like ModelTraceContext, ModelValidationContext, etc.

    Use Cases:
        - Capturing detailed error context for debugging
        - Structured error logging and monitoring
        - API error responses with consistent format
        - Error aggregation in reducers and orchestrators
        - Type-safe error context with domain-specific models

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        error_code: Unique identifier for the error type (e.g., "VALIDATION_ERROR").
        error_type: Category of error - "validation", "runtime", or "system".
        error_message: Human-readable error description.
        component: Optional name of the component where error occurred.
        operation: Optional name of the operation being performed.
        timestamp: When the error occurred (defaults to current UTC time).
        stack_trace: Optional list of stack trace lines for debugging.
        inner_errors: Optional list of nested ModelErrorDetails for error chains.
            Recommended max depth: 5 levels to prevent excessive nesting and memory issues.
        request_id: Optional UUID for request correlation.
        user_id: Optional UUID of the user who triggered the error.
        session_id: Optional UUID for session tracking.
        context_data: Additional typed context. Accepts either a typed model
            (when parameterized) or dict[str, ModelSchemaValue] (default).
        retry_after_seconds: Optional hint for when to retry (rate limiting).
        recovery_suggestions: Optional list of recovery actions.
        documentation_url: Optional link to relevant documentation.

    Example:
        Basic error details (backwards compatible)::

            from omnibase_core.models.services import ModelErrorDetails

            error = ModelErrorDetails(
                error_code="VALIDATION_ERROR",
                error_type="validation",
                error_message="Invalid input format",
                component="UserService",
                operation="create_user",
            )

        Error with recovery information::

            error = ModelErrorDetails(
                error_code="RATE_LIMIT_EXCEEDED",
                error_type="rate_limit",
                error_message="Too many requests",
                retry_after_seconds=60,
                recovery_suggestions=[
                    "Wait 60 seconds before retrying",
                    "Consider using exponential backoff",
                ],
            )

        With typed context (generic usage)::

            from pydantic import BaseModel, ConfigDict

            class ValidationContext(BaseModel):
                model_config = ConfigDict(frozen=True)
                field_name: str
                expected: str
                actual: str

            error = ModelErrorDetails[ValidationContext](
                error_code="VAL001",
                error_type="validation",
                error_message="Invalid field value",
                context_data=ValidationContext(
                    field_name="email",
                    expected="valid email format",
                    actual="not-an-email",
                ),
            )

        Nested errors for error chains::

            inner = ModelErrorDetails(
                error_code="DB_CONNECTION_FAILED",
                error_type="system",
                error_message="Could not connect to database",
            )
            outer = ModelErrorDetails(
                error_code="USER_CREATION_FAILED",
                error_type="runtime",
                error_message="Failed to create user",
                inner_errors=[inner],
            )

        Migrating from dict[str, Any]::

            # Before (untyped)
            error_details = {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
            }

            # After (typed) - use from_dict for legacy format
            error = ModelErrorDetails.from_dict(error_details)

    See Also:
        - ModelOnexError: Primary error class using this model
        - ModelSchemaValue: Type-safe values for context_data
        - MIGRATING_FROM_DICT_ANY.md: Full migration guide

    """

    # Error identification
    error_code: str = Field(default=..., description="Error code")
    error_type: str = Field(
        default=..., description="Error type (validation/runtime/system)"
    )
    error_message: str = Field(default=..., description="Error message")

    # Error context
    component: str | None = Field(
        default=None, description="Component where error occurred"
    )
    operation: str | None = Field(default=None, description="Operation being performed")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Error timestamp",
    )

    # Error details
    stack_trace: list[str] | None = Field(default=None, description="Stack trace lines")
    # Note: type: ignore[type-arg] is intentional here. inner_errors needs to accept
    # ANY ModelErrorDetails variant (with any TContext), not just the same TContext as
    # the parent. This enables flexible error chaining where a validation error (with
    # ValidationContext) can contain a network error (with TraceContext) as an inner error.
    inner_errors: list[ModelErrorDetails] | None = Field(  # type: ignore[type-arg]
        default=None,
        description=(
            "Nested errors for error chaining. Recommended max depth: 5 levels "
            "to prevent excessive nesting and memory issues. Each inner error "
            "can have its own context type."
        ),
    )

    # Contextual data
    request_id: UUID | None = Field(default=None, description="Request ID")
    user_id: UUID | None = Field(default=None, description="User ID")
    session_id: UUID | None = Field(default=None, description="Session ID")

    # Additional context - supports both typed context (TContext) and dict
    context_data: TContext | dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Additional error context. Can be a typed context model or dict.",
    )

    # Recovery information
    retry_after_seconds: int | None = Field(
        default=None,
        description="Retry after seconds",
        ge=0,
    )
    recovery_suggestions: list[str] | None = Field(
        default=None,
        description="Recovery suggestions",
    )
    documentation_url: str | None = Field(default=None, description="Documentation URL")

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    # ONEX_EXCLUDE: dict_str_any - factory input
    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ModelErrorDetails | None:  # type: ignore[type-arg]
        """Create ModelErrorDetails from a dictionary.

        This factory method provides easy migration from legacy dict[str, Any]
        patterns to the typed ModelErrorDetails. It handles common legacy field
        name variations automatically.

        Legacy Field Mappings:
            - ``code`` -> ``error_code``
            - ``message`` -> ``error_message``
            - Missing ``error_type`` defaults to ``"runtime"``

        Args:
            data: Dictionary containing error details. If None, returns None.

        Returns:
            ModelErrorDetails instance if data is provided, None otherwise.

        Raises:
            ValidationError: If required fields are missing after mapping.

        Example:
            Legacy format migration::

                # Old format with 'code' and 'message'
                legacy = {"code": "ERR_001", "message": "Something went wrong"}
                error = ModelErrorDetails.from_dict(legacy)
                assert error.error_code == "ERR_001"
                assert error.error_message == "Something went wrong"
                assert error.error_type == "runtime"  # Default

            Modern format::

                modern = {
                    "error_code": "VALIDATION_ERROR",
                    "error_type": "validation",
                    "error_message": "Invalid input",
                }
                error = ModelErrorDetails.from_dict(modern)

        Note:
            This method does NOT mutate the input dictionary. A defensive
            copy is made before any modifications to preserve caller's data.

            This method returns an unparameterized ModelErrorDetails instance,
            losing generic type information. For typed context, instantiate
            ModelErrorDetails[TContext] directly instead of using this factory
            method.

        """
        if data is None:
            return None

        # Make a defensive copy to avoid mutating the caller's input
        data = data.copy()

        # Handle legacy format - convert legacy field names to standard names
        # and remove unused legacy fields (required for extra="forbid")
        if "error_code" not in data and "code" in data:
            data["error_code"] = data.pop("code")
        elif "code" in data:
            del data["code"]  # Remove unused legacy field

        if "error_type" not in data:
            data["error_type"] = "runtime"

        if "error_message" not in data and "message" in data:
            data["error_message"] = data.pop("message")
        elif "message" in data:
            del data["message"]  # Remove unused legacy field

        return cls(**data)

    def is_retryable(self) -> bool:
        """Check if this error is retryable.

        An error is considered retryable if:

        1. ``retry_after_seconds`` is set (explicit retry hint), OR
        2. ``error_type`` is "timeout" or "rate_limit" (transient errors)

        This method helps implement retry logic in effect nodes and
        orchestrators by identifying errors that may succeed on retry.

        Returns:
            True if the error is retryable, False otherwise.

        Example:
            Retry logic in an effect node::

                try:
                    result = await execute_effect()
                except EffectError as e:
                    if e.details and e.details.is_retryable():
                        wait_time = e.details.retry_after_seconds or 5
                        await asyncio.sleep(wait_time)
                        result = await execute_effect()  # Retry
                    else:
                        raise  # Non-retryable error

        See Also:
            - retry_after_seconds: Explicit retry delay hint
            - ModelEffectRetryPolicy: Retry policy configuration

        """
        return self.retry_after_seconds is not None or self.error_type in [
            "timeout",
            "rate_limit",
        ]

    @field_serializer("timestamp")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """Serialize datetime to ISO 8601 format string.

        This explicit serializer ensures consistent string output in BOTH
        model_dump() (Python mode) AND model_dump(mode='json'). This differs
        from Pydantic's default behavior where model_dump() preserves datetime
        objects.

        Design Rationale:
            ModelErrorDetails is frequently logged/dumped for debugging, where
            consistent string output simplifies error analysis. Context models
            (ModelRetryContext, etc.) intentionally do NOT have explicit
            serializers to preserve datetime objects for programmatic access
            (comparisons, arithmetic operations).

        Format Notes:
            - Uses isoformat() which produces "+00:00" for UTC timezone
            - Pydantic's default JSON serialization uses "Z" for UTC
            - Both are valid ISO 8601 and universally interoperable

        Args:
            value: The datetime value to serialize, or None.

        Returns:
            ISO 8601 formatted string (e.g., "2025-01-15T10:30:00+00:00")
            if value is provided, None otherwise.

        Example:
            Serialization behavior::

                from datetime import datetime, UTC

                error = ModelErrorDetails(
                    error_code="TEST",
                    error_type="runtime",
                    error_message="Test error",
                    timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC),
                )
                data = error.model_dump()
                assert data["timestamp"] == "2025-01-15T10:30:00+00:00"

        """
        if value:
            return value.isoformat()
        return None
