"""Runtime directive payload model for typed directive parameters.

This module provides ModelRuntimeDirectivePayload, a typed context model for
runtime directive payloads. This replaces dict[str, Any] payloads with a
structured model for type safety and validation.

The payload structure supports all EnumDirectiveType values:
    - SCHEDULE_EFFECT: handler_args, execution_mode, priority
    - ENQUEUE_HANDLER: handler_args, priority, queue_name
    - RETRY_WITH_BACKOFF: backoff_base_ms, backoff_multiplier, jitter_ms
    - DELAY_UNTIL: execute_at (absolute timestamp)
    - CANCEL_EXECUTION: cancellation_reason, cleanup_required

Thread Safety:
    ModelRuntimeDirectivePayload instances are immutable (frozen=True) after
    creation, making them thread-safe for concurrent read access.

See Also:
    - ModelRuntimeDirective: Uses this as Generic[TContext] payload
    - EnumDirectiveType: Directive type enumeration
    - ModelRetryContext: Related retry context model
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.utils.util_decorators import allow_dict_str_any

# Maximum nesting depth for handler_args to prevent DoS via deeply nested structures
_MAX_HANDLER_ARGS_DEPTH = 10

# Reserved keys that could cause security issues (prototype pollution prevention)
_RESERVED_KEYS = frozenset({"__proto__", "constructor", "__class__"})


def _check_depth(obj: Any, current_depth: int = 0) -> int:
    """Recursively check the depth of a nested structure.

    Args:
        obj: The object to check depth for.
        current_depth: The current depth level (0 for root).

    Returns:
        The maximum depth found in the structure.

    Note:
        Returns early if current_depth exceeds _MAX_HANDLER_ARGS_DEPTH
        to avoid unnecessary traversal of deeply nested structures.
    """
    if current_depth > _MAX_HANDLER_ARGS_DEPTH:
        return current_depth
    if isinstance(obj, dict):
        if not obj:
            return current_depth
        return max(_check_depth(v, current_depth + 1) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        if not obj:
            return current_depth
        return max(_check_depth(item, current_depth + 1) for item in obj)
    return current_depth


__all__ = ["ModelRuntimeDirectivePayload"]


@allow_dict_str_any(
    "handler_args must remain dict[str, Any] because handler signatures vary widely. "
    "Each handler defines its own parameter schema, and runtime directives must be able "
    "to pass arbitrary keyword arguments. Type safety is enforced at the handler level."
)
class ModelRuntimeDirectivePayload(BaseModel):
    """Typed payload for runtime directives (internal runtime control).

    This model provides structured fields for directive-specific parameters,
    replacing untyped dict[str, Any] payloads with validated fields.

    All fields are optional to support different EnumDirectiveType values:
        - SCHEDULE_EFFECT: Uses handler_args, execution_mode, priority
        - ENQUEUE_HANDLER: Uses handler_args, priority, queue_name
        - RETRY_WITH_BACKOFF: Uses backoff_base_ms, backoff_multiplier, jitter_ms
        - DELAY_UNTIL: Uses execute_at
        - CANCEL_EXECUTION: Uses cancellation_reason, cleanup_required

    Use Cases:
        - Passing arguments to scheduled effect handlers
        - Configuring retry backoff parameters
        - Specifying execution timing for delayed directives
        - Providing cancellation context and cleanup flags

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        handler_args: Keyword arguments to pass to the target handler.
        execution_mode: Sync or async execution mode ('sync' or 'async').
        priority: Queue priority (lower values = higher priority).
        queue_name: Target queue name for enqueued handlers.
        backoff_base_ms: Base delay in milliseconds for exponential backoff.
        backoff_multiplier: Multiplier for exponential backoff growth.
        jitter_ms: Random jitter range in milliseconds to prevent thundering herd.
        execute_at: Absolute timestamp for delayed execution.
        cancellation_reason: Human-readable reason for cancellation.
        cleanup_required: Whether cleanup operations should be performed.

    Example:
        Schedule effect directive payload::

            from omnibase_core.models.context import ModelRuntimeDirectivePayload

            payload = ModelRuntimeDirectivePayload(
                handler_args={"user_id": "123", "action": "notify"},
                execution_mode="async",
                priority=1,
            )

        Retry with backoff payload::

            payload = ModelRuntimeDirectivePayload(
                backoff_base_ms=1000,
                backoff_multiplier=2.0,
                jitter_ms=100,
            )

        Cancel execution payload::

            payload = ModelRuntimeDirectivePayload(
                cancellation_reason="Timeout exceeded",
                cleanup_required=True,
            )

        Delay until payload::

            from datetime import datetime, timedelta, UTC

            payload = ModelRuntimeDirectivePayload(
                execute_at=datetime.now(UTC) + timedelta(minutes=5),
            )

    See Also:
        - ModelRuntimeDirective: Parent model that uses this payload
        - EnumDirectiveType: Defines directive types
        - ModelRetryContext: For error retry tracking
        - ModelOperationalContext: For operation metadata
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    # Handler execution parameters (SCHEDULE_EFFECT, ENQUEUE_HANDLER)
    handler_args: dict[str, Any] = Field(
        default_factory=dict,
        description="Keyword arguments to pass to the target handler",
    )

    @field_validator("handler_args")
    @classmethod
    def validate_handler_args(cls, v: dict[str, Any]) -> dict[str, Any]:
        """Validate handler_args for security concerns.

        This validator enforces defensive boundary validation:
        1. Rejects reserved keys that could cause prototype pollution
        2. Limits nesting depth to prevent DoS attacks

        Args:
            v: The handler_args dictionary to validate.

        Returns:
            The validated dictionary if all checks pass.

        Raises:
            ValueError: If reserved keys are found or depth exceeds limit.
        """
        # Check for reserved keys (prototype pollution prevention)
        found_reserved = _RESERVED_KEYS & set(v.keys())
        if found_reserved:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"handler_args cannot contain reserved keys: {sorted(found_reserved)}. "
                "These keys are reserved to prevent prototype pollution attacks."
            )

        # Check max depth to prevent deeply nested structures
        depth = _check_depth(v)
        if depth > _MAX_HANDLER_ARGS_DEPTH:
            # error-ok: Pydantic field_validator requires ValueError
            raise ValueError(
                f"handler_args exceeds maximum nesting depth of {_MAX_HANDLER_ARGS_DEPTH}. "
                f"Found depth: {depth}. Deeply nested structures are rejected to prevent "
                "denial-of-service attacks."
            )

        return v

    execution_mode: str | None = Field(
        default=None,
        description="Execution mode for handler invocation ('sync' or 'async')",
    )

    # Queue and priority parameters (ENQUEUE_HANDLER)
    priority: int | None = Field(
        default=None,
        description="Queue priority (lower values = higher priority, 0 is highest)",
        ge=0,
    )
    queue_name: str | None = Field(
        default=None,
        description="Target queue name for enqueued handlers",
    )

    # Retry backoff parameters (RETRY_WITH_BACKOFF)
    backoff_base_ms: int | None = Field(
        default=None,
        description="Base delay in milliseconds for exponential backoff",
        ge=0,
    )
    backoff_multiplier: float | None = Field(
        default=None,
        description="Multiplier for exponential backoff growth (e.g., 2.0 for doubling)",
        gt=0.0,
    )
    jitter_ms: int | None = Field(
        default=None,
        description="Random jitter range in milliseconds to prevent thundering herd",
        ge=0,
    )

    # Timing parameters (DELAY_UNTIL)
    execute_at: datetime | None = Field(
        default=None,
        description="Absolute timestamp for delayed execution (UTC recommended)",
    )

    # Cancellation parameters (CANCEL_EXECUTION)
    cancellation_reason: str | None = Field(
        default=None,
        description="Human-readable reason for cancellation",
    )
    cleanup_required: bool = Field(
        default=False,
        description="Whether cleanup operations should be performed on cancellation",
    )
