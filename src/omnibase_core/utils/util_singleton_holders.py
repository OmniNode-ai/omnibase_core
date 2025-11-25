"""
Singleton Holders - Centralized re-exports for DI container infrastructure.

This module provides centralized access to all singleton holder classes,
supporting the DI container pattern with fallback mechanisms for bootstrap
and circular dependency scenarios.
"""

from omnibase_core.utils.util_action_registry_holder import _ActionRegistryHolder
from omnibase_core.utils.util_command_registry_holder import _CommandRegistryHolder
from omnibase_core.utils.util_container_holder import _ContainerHolder
from omnibase_core.utils.util_event_type_registry_holder import _EventTypeRegistryHolder
from omnibase_core.utils.util_logger_cache import _LoggerCache
from omnibase_core.utils.util_protocol_cache_holder import _ProtocolCacheHolder
from omnibase_core.utils.util_secret_manager_holder import _SecretManagerHolder
from omnibase_core.utils.util_simple_fallback_logger import _SimpleFallbackLogger

__all__ = [
    "_ActionRegistryHolder",
    "_CommandRegistryHolder",
    "_ContainerHolder",
    "_EventTypeRegistryHolder",
    "_LoggerCache",
    "_ProtocolCacheHolder",
    "_SecretManagerHolder",
    "_SimpleFallbackLogger",
]
