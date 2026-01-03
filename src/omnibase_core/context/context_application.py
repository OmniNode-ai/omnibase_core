"""Application context for ONEX framework.

This module provides context-variable based container management
using Python's contextvars for thread-safe and async-safe isolation.

Key Benefits:
    - contextvars provide proper isolation between async tasks and threads
    - Each task/thread can have its own container context
    - Supports nested contexts with token-based reset
    - No global mutable state that can cause race conditions

Thread Safety:
    contextvars are inherently thread-safe and async-safe:
    - Each thread has its own copy of context variables
    - asyncio tasks inherit context at creation time
    - Modifications in one task don't affect others

"""

from __future__ import annotations

import contextvars
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer


# Context variable for the current container
# Default is None, meaning no container is set in the current context
_current_container: contextvars.ContextVar[ModelONEXContainer | None] = (
    contextvars.ContextVar("onex_container", default=None)
)


class ApplicationContext:
    """Application context manager for ONEX containers.

    This class provides a structured way to manage container contexts,
    with proper setup and teardown semantics.

    Usage:
        container = await create_model_onex_container()

        # Async context manager
        async with ApplicationContext(container):
            # Container is available via get_current_container()
            current = get_current_container()
            assert current is container

        # Sync context manager
        with ApplicationContext.sync(container):
            current = get_current_container()
            assert current is container

    Attributes:
        container: The ModelONEXContainer instance for this context
        token: The contextvars token for reset (set when entering context)
    """

    def __init__(self, container: ModelONEXContainer) -> None:
        """Initialize application context with a container.

        Args:
            container: The ModelONEXContainer instance to use in this context
        """
        self._container = container
        self._token: contextvars.Token[ModelONEXContainer | None] | None = None

    @property
    def container(self) -> ModelONEXContainer:
        """Get the container for this context."""
        return self._container

    async def __aenter__(self) -> ApplicationContext:
        """Enter async context and set the container.

        Returns:
            Self for use in 'async with' statements
        """
        self._token = set_current_container(self._container)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit async context and reset the container.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if self._token is not None:
            reset_container(self._token)
            self._token = None

    def __enter__(self) -> ApplicationContext:
        """Enter sync context and set the container.

        Returns:
            Self for use in 'with' statements
        """
        self._token = set_current_container(self._container)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Exit sync context and reset the container.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if self._token is not None:
            reset_container(self._token)
            self._token = None

    @classmethod
    def sync(cls, container: ModelONEXContainer) -> ApplicationContext:
        """Create a sync context manager for the container.

        This is a convenience method that returns self, since
        ApplicationContext supports both sync and async context protocols.

        Args:
            container: The ModelONEXContainer instance to use

        Returns:
            ApplicationContext instance for use with 'with' statement
        """
        return cls(container)


def get_current_container() -> ModelONEXContainer | None:
    """Get the container from the current context.

    This function returns the container that was set in the current
    execution context (thread, async task, etc.). If no container
    has been set, returns None.

    Returns:
        The current ModelONEXContainer instance, or None if not set

    Example:
        container = get_current_container()
        if container is not None:
            service = container.get_service(ProtocolLogger)
    """
    return _current_container.get()


def set_current_container(
    container: ModelONEXContainer,
) -> contextvars.Token[ModelONEXContainer | None]:
    """Set the container in the current context.

    This function sets the container for the current execution context.
    It returns a token that can be used to reset the container to its
    previous value.

    Args:
        container: The ModelONEXContainer instance to set

    Returns:
        A Token that can be passed to reset_container() to restore
        the previous value

    Example:
        token = set_current_container(my_container)
        try:
            # Use container
            pass
        finally:
            reset_container(token)
    """
    return _current_container.set(container)


def reset_container(token: contextvars.Token[ModelONEXContainer | None]) -> None:
    """Reset container to previous value using token.

    This function resets the container to whatever value it had before
    the corresponding set_current_container() call.

    Args:
        token: The token returned by set_current_container()

    Example:
        token = set_current_container(my_container)
        try:
            # Use container
            pass
        finally:
            reset_container(token)
    """
    _current_container.reset(token)


@asynccontextmanager
async def run_with_container(
    container: ModelONEXContainer,
) -> AsyncIterator[ModelONEXContainer]:
    """Async context manager to run code with a specific container.

    This provides a convenient way to run async code with a container
    set in the context, automatically cleaning up afterwards.

    Args:
        container: The ModelONEXContainer instance to use

    Yields:
        The container instance

    Example:
        async with run_with_container(my_container) as container:
            # container is now the current container
            service = container.get_service(ProtocolLogger)
    """
    token = set_current_container(container)
    try:
        yield container
    finally:
        reset_container(token)


@contextmanager
def run_with_container_sync(
    container: ModelONEXContainer,
) -> Iterator[ModelONEXContainer]:
    """Sync context manager to run code with a specific container.

    This provides a convenient way to run sync code with a container
    set in the context, automatically cleaning up afterwards.

    Args:
        container: The ModelONEXContainer instance to use

    Yields:
        The container instance

    Example:
        with run_with_container_sync(my_container) as container:
            # container is now the current container
            service = container.get_service(ProtocolLogger)
    """
    token = set_current_container(container)
    try:
        yield container
    finally:
        reset_container(token)
