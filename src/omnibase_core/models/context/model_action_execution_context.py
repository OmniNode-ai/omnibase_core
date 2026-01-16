"""
Action execution context model for action/node execution.

This module provides ModelActionExecutionContext, a typed model for execution-related
metadata that replaces untyped dict[str, ModelSchemaValue] fields. It captures
execution configuration, timeout settings, retry behavior, and debugging options.

Note:
    This model is distinct from ModelExecutionContext in models/core/ which is
    used for CLI execution. This model (ModelActionExecutionContext) is specifically
    for action/node execution context within the typed context system.

Thread Safety:
    ModelActionExecutionContext is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_authorization_context: Auth context
    - omnibase_core.models.core.model_execution_context: CLI execution context
"""

from typing import Literal, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.constants import TIMEOUT_DEFAULT_MS

__all__ = ["ModelActionExecutionContext"]


class ModelActionExecutionContext(BaseModel):
    """Action execution context for action/node execution.

    Provides typed execution configuration including environment settings,
    timeout and retry policies, and debugging options. All fields have
    sensible defaults suitable for development environments.

    Attributes:
        node_id: Unique identifier of the node executing the action. Used for
            tracing and debugging to identify which node processed a request.
        workflow_id: Parent workflow identifier (UUID) when the action is part of a
            larger workflow execution. Enables workflow-level tracing.
        environment: Execution environment name. Controls environment-specific
            behavior like logging levels, external service endpoints, and
            feature flags. Must be one of: development, staging, production.
        timeout_ms: Maximum execution time in milliseconds before the action
            is terminated. Prevents runaway processes and resource exhaustion.
            Uses milliseconds for consistency with ONEX timeout conventions.
        retry_count: Current retry attempt number (0-indexed). Allows actions
            to adjust behavior based on retry state (e.g., exponential backoff).
        max_retries: Maximum number of retry attempts before permanent failure.
            Set to 0 to disable retries entirely.
        dry_run: When True, the action should simulate execution without
            producing side effects. Useful for testing and validation.
        debug_mode: When True, enables verbose debug logging for the action.
            May impact performance; use only for troubleshooting.
        trace_enabled: When True, enables distributed tracing instrumentation.
            Captures timing and dependency information for observability.
        correlation_id: Request correlation identifier for distributed tracing.
            Links related requests across services for end-to-end visibility.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from uuid import UUID
        >>> from omnibase_core.models.context import ModelActionExecutionContext
        >>>
        >>> context = ModelActionExecutionContext(
        ...     node_id="node_abc123",
        ...     workflow_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        ...     environment="production",
        ...     timeout_ms=60000,
        ...     dry_run=False,
        ... )
        >>> context.environment
        'production'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str | None = Field(
        default=None,
        description="Node identifier executing the action",
    )
    workflow_id: UUID | None = Field(
        default=None,
        description="Parent workflow identifier (UUID)",
    )
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description=(
            "Execution environment. Controls environment-specific behavior like "
            "logging levels and feature flags. Must be: development, staging, or production."
        ),
    )
    timeout_ms: int = Field(
        default=TIMEOUT_DEFAULT_MS,
        ge=1,
        description=(
            "Execution timeout in milliseconds. Minimum 1 millisecond. "
            "Default is TIMEOUT_DEFAULT_MS (30 seconds). Uses milliseconds for "
            "consistency with ONEX timeout conventions. "
            "See omnibase_core.constants for timeout constant values."
        ),
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description="Current retry attempt number (0-indexed)",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum retry attempts before permanent failure",
    )
    dry_run: bool = Field(
        default=False,
        description="Simulate execution without side effects",
    )
    debug_mode: bool = Field(
        default=False,
        description="Enable verbose debug logging",
    )
    trace_enabled: bool = Field(
        default=False,
        description="Enable distributed tracing instrumentation",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for distributed tracing",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(
        cls, v: str
    ) -> Literal["development", "staging", "production"]:
        """Validate that environment is one of the allowed values.

        Args:
            v: The environment string to validate.

        Returns:
            The validated environment as a Literal type (lowercase).

        Raises:
            ValueError: If the value is not a string or not a valid environment.
        """
        if not isinstance(v, str):
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(f"environment must be a string, got {type(v).__name__}")
        normalized = v.lower().strip()
        allowed = {"development", "staging", "production"}
        if normalized not in allowed:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"Invalid environment '{v}': must be one of {sorted(allowed)}"
            )
        # Validated via set membership check above
        return cast(Literal["development", "staging", "production"], normalized)
