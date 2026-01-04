"""Singleton holder utilities.

DEPRECATED: All singleton holders have been removed in favor of:
- ApplicationContext for container management (contextvars-based)
- functools.lru_cache for caching

For container management, use the ApplicationContext:
    from omnibase_core.context import (
        get_current_container,
        set_current_container,
        reset_container,
        run_with_container,
        ApplicationContext,
    )

Migration from legacy patterns:
    # Old pattern (no longer available):
    # from omnibase_core.utils.util_singleton_holders import _ContainerHolder
    # container = _ContainerHolder.get()
    # _ContainerHolder.set(container)

    # New pattern:
    from omnibase_core.context import get_current_container, set_current_container
    container = get_current_container()
    token = set_current_container(container)
    # ... use container ...
    reset_container(token)

    # Or use context manager:
    from omnibase_core.context import ApplicationContext
    with ApplicationContext(container):
        # container is available via get_current_container()
        pass

Removed holders (all migrated):
- _ContainerHolder -> omnibase_core.context.ApplicationContext
- _ActionRegistryHolder -> container.action_registry()
- _CommandRegistryHolder -> container.command_registry()
- _EventTypeRegistryHolder -> container.event_type_registry()
- _SecretManagerHolder -> container.secret_manager()
- _LoggerCache -> logging_core._get_cached_logger()
- _ProtocolCacheHolder -> logging_emit.get_protocol_services()
- _SimpleFallbackLogger -> logging_core._get_cached_logger()

This module exports nothing as all patterns have been migrated.
"""

# No exports - all singletons removed
__all__: list[str] = []
