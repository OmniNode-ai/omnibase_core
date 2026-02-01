"""Operational context model for operation-level metadata.

This module provides ModelOperationalContext, a typed context model for
tracking operation identifiers, names, and timeout configurations.

Thread Safety:
    ModelOperationalContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelTraceContext: Distributed tracing context
    - ModelRetryContext: Retry-specific metadata
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ModelOperationalContext(BaseModel):
    """Typed context for operation-level metadata.

    This model provides structured fields for tracking individual operations,
    including identifiers, names, and timeout configurations.

    Use Cases:
        - Operation tracking in orchestrators
        - Timeout management for effect nodes
        - Operation logging and monitoring
        - Error context for failed operations

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        operation_id: Unique identifier for this specific operation instance.
        operation_name: Human-readable name describing the operation.
        timeout_ms: Optional timeout in milliseconds for the operation.

    Example:
        Basic operational context::

            from omnibase_core.models.context import ModelOperationalContext
            from uuid import uuid4

            context = ModelOperationalContext(
                operation_id=uuid4(),
                operation_name="create_user",
                timeout_ms=5000,
            )

        Minimal context (operation_name is required)::

            context = ModelOperationalContext(
                operation_name="validate_input",
            )

    See Also:
        - ModelTraceContext: For distributed tracing
        - ModelRetryContext: For retry-specific metadata
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    operation_id: uuid.UUID | None = Field(
        default=None,
        description="Unique identifier for this specific operation instance",
    )
    operation_name: str = Field(
        description="Human-readable name describing the operation",
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Timeout in milliseconds for the operation",
        ge=0,
    )
