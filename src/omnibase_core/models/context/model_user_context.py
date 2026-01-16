"""User context model for user and session tracking.

This module provides ModelUserContext, a typed context model for
tracking user identifiers, session IDs, and tenant information.

Thread Safety:
    ModelUserContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelResourceContext: Resource-related context
    - ModelTraceContext: Distributed tracing context
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ModelUserContext(BaseModel):
    """Typed context for user and session tracking.

    This model provides structured fields for tracking user identities,
    session information, and multi-tenant isolation.

    Use Cases:
        - User identity tracking in requests
        - Session management and correlation
        - Multi-tenant isolation and routing
        - Audit logging with user context

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        user_id: Unique identifier for the authenticated user.
        session_id: Unique identifier for the user's current session.
        tenant_id: Identifier for the tenant in multi-tenant systems.

    Example:
        Full user context::

            from omnibase_core.models.context import ModelUserContext
            from uuid import uuid4

            context = ModelUserContext(
                user_id=uuid4(),
                session_id=uuid4(),
                tenant_id=uuid4(),
            )

        Minimal context (user_id is required)::

            context = ModelUserContext(
                user_id=uuid4(),
            )

    See Also:
        - ModelResourceContext: For resource identification
        - ModelTraceContext: For distributed tracing
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    user_id: uuid.UUID = Field(
        description="Unique identifier for the authenticated user",
    )
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Unique identifier for the user's current session",
    )
    tenant_id: uuid.UUID | None = Field(
        default=None,
        description="Identifier for the tenant in multi-tenant systems",
    )
