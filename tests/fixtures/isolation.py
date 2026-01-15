"""Test isolation fixtures for parallel-safe test execution.

This module provides fixtures to reset context variables and clear caches
for parallel tests. Essential for pytest-xdist parallel execution.

Architecture Note:
    The codebase uses contextvars for container management (ApplicationContext)
    and lru_cache patterns for other cached services. This provides proper
    isolation between async tasks and threads.

Thread Safety:
    contextvars are inherently thread-safe and async-safe:
    - Each thread has its own copy of context variables
    - asyncio tasks inherit context at creation time
    - Modifications in one task don't affect others

Usage:
    @pytest.fixture(autouse=True)
    def isolated_test(reset_all_singletons):
        # Test runs with clean context
        pass

    def test_container_isolation(reset_container_singleton):
        # Only container context is reset
        pass
"""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# Legacy holder keys that have been migrated to lru_cache patterns or contextvars
# Kept for documentation and backward compatibility checks
LEGACY_HOLDER_KEYS: frozenset[str] = frozenset(
    {
        "action_registry",
        "command_registry",
        "event_type_registry",
        "logger_cache",
        "protocol_cache",
        "secret_manager",
        "container",  # Now uses ApplicationContext (contextvars)
    }
)


def reset_application_context() -> contextvars.Token[Any] | None:
    """Reset the application context container to None.

    This function resets the contextvar-based container management system.
    Unlike the legacy singleton pattern, contextvars provide proper isolation
    between async tasks and threads.

    Returns:
        Token that can be used to restore the previous value, or None if
        the context module is not available.

    Thread Safety:
        contextvars are inherently thread-safe. Each thread has its own
        copy of context variables, so this only affects the current context.
    """
    try:
        from omnibase_core.context.context_application import _current_container

        return _current_container.set(None)
    except ImportError:
        return None


def restore_application_context(token: contextvars.Token[Any] | None) -> None:
    """Restore the application context to its previous value.

    Args:
        token: Token from reset_application_context() call.
    """
    if token is None:
        return

    try:
        from omnibase_core.context.context_application import _current_container

        _current_container.reset(token)
    except ImportError:
        pass


def clear_all_caches() -> None:
    """Clear all lru_cache caches and reset application context.

    This function clears caches that replaced the old singleton holder pattern
    and resets the contextvar-based application context.
    Call this for test isolation instead of resetting individual holders.

    Thread Safety:
        - Each cache clearing function handles its own thread safety.
        - Application context reset only affects the current execution context.
    """
    # Reset application context (contextvar-based container management)
    reset_application_context()

    # Clear logger cache (replaces _LoggerCache holder)
    try:
        from omnibase_core.logging.logging_core import clear_logger_cache

        clear_logger_cache()
    except ImportError:
        pass

    # Clear protocol cache (replaces _ProtocolCacheHolder)
    try:
        from omnibase_core.logging.logging_emit import clear_protocol_cache

        clear_protocol_cache()
    except ImportError:
        pass


@dataclass
class ContextState:
    """Captured state for context variables.

    Attributes:
        token: The contextvars token for reset.
        container_value: The captured container value.
        extra_state: Additional state for complex scenarios.
    """

    token: contextvars.Token[Any] | None
    container_value: ModelONEXContainer | None = None
    extra_state: dict[str, Any] = field(default_factory=dict)


class SingletonResetContext:
    """Context manager for resetting context variables and clearing caches.

    Thread Safety:
        Uses contextvars which provide inherent thread safety and async safety.

    Architecture Note:
        This class handles the container context variable via ApplicationContext.
        Other cached services are handled via clear_all_caches() which clears
        lru_cache instances.

    Usage:
        # Reset container context and clear all caches
        with SingletonResetContext():
            # Test code with clean state
            pass

        # Reset only container context (legacy key still accepted)
        with SingletonResetContext(holder_keys=["container"]):
            pass

    Args:
        holder_keys: List of holder keys to reset (None = all).
            Valid keys: container (uses contextvars now)
            Note: All keys are legacy and use contextvars/caches now.
        reset_to_none: If True, reset context to None on entry.
            If False, just restore on exit.
        clear_caches: If True (default), also clear lru_cache caches.
    """

    def __init__(
        self,
        holder_keys: list[str] | None = None,
        reset_to_none: bool = True,
        clear_caches: bool = True,
    ) -> None:
        """Initialize the context manager.

        Args:
            holder_keys: Keys of holders to reset (None = all).
            reset_to_none: Reset to None on entry if True.
            clear_caches: Clear lru_cache caches if True.
        """
        # Accept "container" key for backward compatibility
        self._should_reset_container = holder_keys is None or "container" in holder_keys
        # Keep filtered keys for backward compatibility with tests checking this
        self._holder_keys = (
            ["container"] if (holder_keys is None or "container" in holder_keys) else []
        )

        self._reset_to_none = reset_to_none
        self._clear_caches = clear_caches
        self._saved_state: ContextState | None = None

    def _save_and_reset_context(self) -> None:
        """Save current context and reset to None."""
        try:
            from omnibase_core.context.context_application import (
                _current_container,
                get_current_container,
            )

            # Save current container value
            container_value = get_current_container()

            # Reset to None if requested, otherwise just capture for restore
            if self._reset_to_none:
                token = _current_container.set(None)
            else:
                # Get current value and set it again to get a token
                current = _current_container.get()
                token = _current_container.set(current)

            self._saved_state = ContextState(
                token=token,
                container_value=container_value,
            )
        except ImportError:
            # Application context module not available
            self._saved_state = ContextState(token=None)

    def _restore_context(self) -> None:
        """Restore context to saved value."""
        if self._saved_state is None or self._saved_state.token is None:
            return

        try:
            from omnibase_core.context.context_application import _current_container

            _current_container.reset(self._saved_state.token)
        except ImportError:
            pass

    def __enter__(self) -> SingletonResetContext:
        """Enter context: save state, reset context, and clear caches."""
        # Save and reset container context
        if self._should_reset_container:
            self._save_and_reset_context()

        # Clear lru_cache caches if requested
        if self._clear_caches:
            clear_all_caches()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit context: restore saved state."""
        if self._should_reset_container:
            self._restore_context()


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def reset_all_singletons() -> Generator[SingletonResetContext, None, None]:
    """Reset ALL context variables and clear caches for test isolation.

    This fixture:
    - Resets the container context variable to None
    - Clears all lru_cache caches (logger, protocol, etc.)
    - Restores original state after test

    Usage:
        def test_something(reset_all_singletons):
            # Container context is reset to None at start
            # All caches are cleared
            # Original values restored after test
            pass

    Yields:
        SingletonResetContext for inspection if needed.
    """
    with SingletonResetContext() as ctx:
        yield ctx


@pytest.fixture
def reset_container_singleton() -> Generator[SingletonResetContext, None, None]:
    """Reset only the container context variable.

    Use this for tests that specifically test container behavior
    without clearing other caches.

    Yields:
        SingletonResetContext for inspection if needed.
    """
    with SingletonResetContext(holder_keys=["container"], clear_caches=False) as ctx:
        yield ctx


@pytest.fixture
def reset_registries() -> Generator[None, None, None]:
    """Reset registry state via container and clear caches.

    This fixture provides test isolation for registry-related tests.
    Since registries are now accessed through the container rather than
    individual singleton holders, this resets the container context and
    clears all caches.

    Note:
        This replaces the old behavior of resetting action_registry,
        command_registry, and event_type_registry holders directly.
        Those holders have been migrated to container-based access.

    Yields:
        None (for backward compatibility with existing tests).
    """
    # Clear caches for registry-related functionality
    clear_all_caches()

    # Reset container context to ensure fresh registry state
    with SingletonResetContext(holder_keys=["container"], clear_caches=True):
        yield


@pytest.fixture
def clear_caches_fixture() -> Generator[None, None, None]:
    """Clear all lru_cache caches for test isolation.

    Use this when you only need cache clearing without context reset.
    Caches are cleared at start and end of test.

    Yields:
        None
    """
    clear_all_caches()
    yield
    clear_all_caches()


@pytest.fixture
def isolated_correlation_context() -> Generator[None, None, None]:
    """Clear thread-local correlation IDs for test isolation.

    This ensures each test starts without any correlation ID
    context from previous tests.

    Usage:
        def test_logging(isolated_correlation_context):
            # No correlation ID set at start
            pass
    """
    # Import the logging module to access _context
    try:
        from omnibase_core.logging import logging_core

        # Save current correlation ID if any
        saved_correlation_id = getattr(logging_core._context, "correlation_id", None)

        # Clear the correlation ID
        if hasattr(logging_core._context, "correlation_id"):
            delattr(logging_core._context, "correlation_id")

        yield

        # Restore original correlation ID
        if saved_correlation_id is not None:
            logging_core._context.correlation_id = saved_correlation_id
        elif hasattr(logging_core._context, "correlation_id"):
            delattr(logging_core._context, "correlation_id")

    except ImportError:
        # If logging module isn't available, just yield
        yield


@pytest.fixture
def fresh_asyncio_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Provide a completely fresh event loop for test isolation.

    This creates a new event loop, sets it as current, and cleans up
    after the test. Essential for parallel tests to avoid loop conflicts.

    Usage:
        async def test_async_operation(fresh_asyncio_loop):
            # Uses fresh isolated event loop
            pass

    Yields:
        The new event loop.

    Note: Exception handling includes FileNotFoundError and OSError to handle
    race conditions during parallel test execution where cleanup may access
    already-deleted files or resources.
    """
    # Save the current event loop if any
    try:
        old_loop = asyncio.get_event_loop()
        old_loop_running = old_loop.is_running()
    except RuntimeError:
        old_loop = None
        old_loop_running = False

    # Create fresh loop
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    try:
        yield new_loop
    finally:
        # Clean up the new loop
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(new_loop)
            for task in pending:
                task.cancel()

            # Give tasks a chance to handle cancellation
            if pending:
                new_loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

            new_loop.close()
        except (FileNotFoundError, OSError):
            # Race condition - files already cleaned up by parallel workers
            pass
        except Exception:
            # Best effort cleanup
            pass

        # Restore old loop if it wasn't running
        if old_loop is not None and not old_loop_running:
            try:
                asyncio.set_event_loop(old_loop)
            except (FileNotFoundError, OSError, RuntimeError):
                # Race condition or loop already closed
                pass
            except Exception:
                pass


@contextmanager
def isolated_singleton(
    holder_key: str,
) -> Iterator[None]:
    """Context manager for isolating container context or clearing caches.

    Convenience function for when you need to isolate the container
    outside of pytest fixtures.

    Args:
        holder_key: Key of the holder to isolate.
            For "container": resets container context
            For legacy keys: clears all caches

    Yields:
        None

    Usage:
        with isolated_singleton("container"):
            # Container context is reset, original restored on exit
            pass
    """
    # All keys result in the same behavior now - clear caches and reset context
    with SingletonResetContext(holder_keys=[holder_key]):
        yield


# =============================================================================
# Utility Functions
# =============================================================================


def get_all_holder_classes() -> dict[str, type[Any]]:
    """Get all singleton holder classes.

    Returns:
        Empty dict - all singleton holders have been removed in favor of
        contextvars and lru_cache patterns.

    Note:
        This function is kept for backward compatibility but returns an
        empty dict since all singleton holders have been removed.
    """
    # No singleton holder classes remain - all migrated to contextvars
    return {}


def reset_singleton_by_key(key: str) -> bool:
    """Reset a specific context or clear cache.

    Thread-safe reset of container context or cache clearing.

    Args:
        key: The key to reset.
            For "container": resets container context
            For legacy keys: clears all caches
            For unknown keys: returns False

    Returns:
        True if reset/clear succeeded, False if key is unknown.
    """
    # Handle container key
    if key == "container":
        reset_application_context()
        return True

    # Handle other legacy keys by clearing caches
    if key in LEGACY_HOLDER_KEYS:
        clear_all_caches()
        return True

    return False


def is_legacy_holder_key(key: str) -> bool:
    """Check if a holder key is a legacy key.

    Legacy keys refer to holders that have been migrated to lru_cache patterns
    or contextvars.

    Args:
        key: The holder key to check.

    Returns:
        True if the key is a legacy key, False otherwise.
    """
    return key in LEGACY_HOLDER_KEYS


def get_current_container_for_test() -> Any:
    """Get the current container from context for testing.

    This is a convenience function for tests that need to check
    the current container state.

    Returns:
        The current container or None if not set.
    """
    try:
        from omnibase_core.context.context_application import get_current_container

        return get_current_container()
    except ImportError:
        return None
