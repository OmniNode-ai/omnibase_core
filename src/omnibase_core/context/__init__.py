"""Application context module for ONEX framework.

This module provides context-variable based container management
using Python's contextvars for thread-safe and async-safe isolation.

Key Features:
    - Thread-safe and async-safe context propagation via contextvars
    - Proper isolation between concurrent contexts (asyncio tasks, threads)
    - Token-based reset capability for testing and scoped contexts
    - Context managers for convenient scoped container access

Usage:
    from omnibase_core.context import (
        get_current_container,
        set_current_container,
        reset_container,
        run_with_container,
        ApplicationContext,
    )

    # Set container for current context
    token = set_current_container(container)

    # Get container in current context
    container = get_current_container()

    # Reset to previous value (for testing/cleanup)
    reset_container(token)

    # Run code with a specific container (async)
    async with run_with_container(container):
        # container is available via get_current_container()
        pass

    # Run code with a specific container (sync)
    with ApplicationContext(container):
        # container is available via get_current_container()
        pass
"""

from omnibase_core.context.context_application import (
    ApplicationContext,
    get_current_container,
    reset_container,
    run_with_container,
    run_with_container_sync,
    set_current_container,
)

__all__ = [
    "ApplicationContext",
    "get_current_container",
    "set_current_container",
    "reset_container",
    "run_with_container",
    "run_with_container_sync",
]
