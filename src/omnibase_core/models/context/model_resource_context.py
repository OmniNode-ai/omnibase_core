"""Resource context model for resource identification.

This module provides ModelResourceContext, a typed context model for
tracking resource identifiers, types, and namespaces.

Thread Safety:
    ModelResourceContext instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access across multiple threads.

See Also:
    - ModelUserContext: User-related context
    - ModelErrorDetails: Error handling with resource context
"""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ModelResourceContext(BaseModel):
    """Typed context for resource identification.

    This model provides structured fields for identifying resources
    by their ID, type, and namespace within a system.

    Use Cases:
        - Resource access tracking
        - Error context for resource operations
        - Audit logging
        - Multi-tenant resource isolation

    Thread Safety:
        Instances are immutable (frozen=True) after creation, making them
        thread-safe for concurrent read access. For pytest-xdist compatibility,
        from_attributes=True is enabled.

    Attributes:
        resource_id: Unique identifier for the specific resource.
        resource_type: Type/category of the resource (e.g., "user", "document").
        namespace: Namespace or scope containing the resource.

    Example:
        Resource context for a document::

            from omnibase_core.models.context import ModelResourceContext
            from uuid import uuid4

            context = ModelResourceContext(
                resource_id=uuid4(),
                resource_type="document",
                namespace="workspace/engineering",
            )

        Minimal resource identification (resource_id is required)::

            context = ModelResourceContext(
                resource_id=uuid4(),
            )

    See Also:
        - ModelUserContext: For user-related context
        - ModelValidationContext: For field-level validation
    """

    model_config = ConfigDict(frozen=True, from_attributes=True, extra="forbid")

    resource_id: uuid.UUID = Field(
        description="Unique identifier for the specific resource",
    )
    resource_type: str | None = Field(
        default=None,
        description="Type/category of the resource (e.g., 'user', 'document')",
    )
    namespace: str | None = Field(
        default=None,
        description="Namespace or scope containing the resource",
    )
