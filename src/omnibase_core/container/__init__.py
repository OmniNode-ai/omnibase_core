"""Container logic module.

This module contains dependency injection container logic and service resolution.
"""

from omnibase_core.container.container_service_resolver import (
    bind_get_service_method,
    create_get_service_method,
)
from omnibase_core.container.service_registry import ServiceRegistry
from omnibase_core.models.container import (
    ModelServiceInstance,
    ModelServiceMetadata,
    ModelServiceRegistration,
    ModelServiceRegistryConfig,
    ModelServiceRegistryStatus,
)
from omnibase_core.models.container.model_onex_container import (
    ModelONEXContainer,
    create_model_onex_container,
    get_model_onex_container,
    get_model_onex_container_sync,
)
from omnibase_core.models.container.model_registry_config import (
    create_default_registry_config,
)

__all__ = [
    "ModelONEXContainer",
    "ModelServiceInstance",
    "ModelServiceMetadata",
    "ModelServiceRegistration",
    "ModelServiceRegistryConfig",
    "ModelServiceRegistryStatus",
    "ServiceRegistry",
    "bind_get_service_method",
    "create_default_registry_config",
    "create_get_service_method",
    "create_model_onex_container",
    "get_model_onex_container",
    "get_model_onex_container_sync",
]
