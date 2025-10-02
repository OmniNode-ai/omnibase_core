"""Container logic module.

This module contains dependency injection container logic and service resolution.
"""

from omnibase_core.container.container_service_resolver import ContainerServiceResolver
from omnibase_core.container.enhanced_container import EnhancedContainer

__all__ = [
    "ContainerServiceResolver",
    "EnhancedContainer",
]
