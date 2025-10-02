"""Container logic module.

This module contains dependency injection container logic and service resolution.
"""

from omnibase_core.container.container_service_resolver import (
    bind_get_service_method,
    create_get_service_method,
)
from omnibase_core.models.container.model_onex_container import (
    ModelONEXContainer,
    create_model_onex_container,
    get_model_onex_container,
    get_model_onex_container_sync,
)

__all__ = [
    "ModelONEXContainer",
    "bind_get_service_method",
    "create_get_service_method",
    "create_model_onex_container",
    "get_model_onex_container",
    "get_model_onex_container_sync",
]
