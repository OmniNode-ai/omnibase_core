"""
Provider models for ONEX framework.

This module provides models for provider-related functionality including
provider descriptors and capability requirements.

Key Models
----------
ModelProviderDescriptor
    Describes a concrete provider instance registered in the registry.
    Contains capabilities, adapter path, connection reference, and health status.
    Uses ModelHealthStatus from omnibase_core.models.health for rich health tracking.

Example Usage
-------------
Creating a provider descriptor:

    >>> from uuid import uuid4
    >>> from omnibase_core.models.providers import ModelProviderDescriptor
    >>>
    >>> descriptor = ModelProviderDescriptor(
    ...     provider_id=uuid4(),  # UUID type
    ...     capabilities=["database.relational", "database.postgresql"],
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     tags=["production", "primary"],
    ... )

Checking provider health:

    >>> from omnibase_core.models.health import ModelHealthStatus
    >>> health = ModelHealthStatus.create_healthy(score=1.0)
    >>> health.status
    'healthy'

Lifecycle Example
-----------------
This example demonstrates the typical lifecycle of a provider descriptor,
from creation through registration, health monitoring, and capability matching:

    >>> from uuid import uuid4
    >>> from omnibase_core.models.providers import ModelProviderDescriptor
    >>> from omnibase_core.models.health import ModelHealthStatus
    >>>
    >>> # 1. CREATE: Define the provider with its capabilities
    >>> provider_id = uuid4()
    >>> descriptor = ModelProviderDescriptor(
    ...     provider_id=provider_id,
    ...     capabilities=["database.relational", "database.postgresql"],
    ...     adapter="omnibase_infra.adapters.PostgresAdapter",
    ...     connection_ref="secrets://postgres/primary",
    ...     attributes={"version": "15.4", "region": "us-east-1"},
    ...     declared_features={"supports_json": True, "max_connections": 100},
    ...     tags=["production", "primary"],
    ... )
    >>>
    >>> # 2. REGISTER: Add to provider registry (conceptual)
    >>> # registry.register(descriptor)  # Would register with actual registry
    >>>
    >>> # 3. HEALTH CHECK: Update health status after probe
    >>> health = ModelHealthStatus.create_healthy(
    ...     score=0.95,
    ...     metrics={"latency_ms": 12.5, "connections_used": 45},
    ... )
    >>> # Create updated descriptor with health (immutable, so use model_copy)
    >>> descriptor_with_health = descriptor.model_copy(update={"health": health})
    >>>
    >>> # 4. FEATURE RESOLUTION: Get effective features
    >>> # Initially uses declared_features (observed_features is empty)
    >>> features = descriptor.get_effective_features()
    >>> features.get("supports_json")
    True
    >>>
    >>> # After runtime probing, observed_features takes precedence
    >>> probed_descriptor = descriptor.model_copy(
    ...     update={"observed_features": {"supports_json": True, "supports_arrays": True}}
    ... )
    >>> probed_descriptor.get_effective_features()
    {'supports_arrays': True, 'supports_json': True}
    >>>
    >>> # 5. CAPABILITY MATCHING: Check for specific capabilities
    >>> # Exact match
    >>> descriptor.has_capability("database.postgresql")
    True
    >>>
    >>> # Pattern matching with wildcards
    >>> descriptor.matches_any_capability(["database.*"])
    True
    >>> descriptor.matches_any_capability(["cache.*"])
    False
    >>>
    >>> # 6. RESOLUTION: Find providers matching requirements (conceptual)
    >>> # matching = registry.resolve(
    >>> #     capabilities=["database.*"],
    >>> #     tags=["production"],
    >>> #     min_health_score=0.9,
    >>> # )

Thread Safety
-------------
All models in this module are immutable (frozen=True) after creation,
making them thread-safe for concurrent read access from multiple threads
or async tasks.

.. versionadded:: 0.4.0
    Initial implementation as part of OMN-1153 provider registry models.
"""

from omnibase_core.models.providers.model_provider_descriptor import (
    ModelProviderDescriptor,
)


def _rebuild_model_provider_descriptor() -> None:
    """Rebuild ModelProviderDescriptor to resolve the ModelHealthStatus forward reference.

    This function is called after all imports are complete to ensure the forward
    reference to ModelHealthStatus (which is imported under TYPE_CHECKING to avoid
    circular imports) can be resolved at runtime.

    The deferred import approach avoids circular import issues by only importing
    ModelHealthStatus when needed for model_rebuild(), not at module load time.
    """
    try:
        # Deferred import to avoid circular import at module load time.
        # Import directly from the module file to minimize import chain.
        from omnibase_core.models.health.model_health_status import (
            ModelHealthStatus,
        )

        # Rebuild with the namespace containing ModelHealthStatus
        ModelProviderDescriptor.model_rebuild(
            _types_namespace={"ModelHealthStatus": ModelHealthStatus}
        )
    except (ImportError, AttributeError):
        # During circular import resolution, this may fail - safe to ignore.
        # The rebuild will succeed when the module is imported through a different path.
        pass


# Attempt to rebuild now. If it fails due to circular imports, it will succeed
# when the model is accessed through a properly ordered import path.
_rebuild_model_provider_descriptor()

__all__ = [
    "ModelProviderDescriptor",
]
