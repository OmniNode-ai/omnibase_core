# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Shared fixtures for service tests.

Provides cleanup utilities to prevent async task warnings and memory leaks.

Session-Level Cleanup:
---------------------
The final_asyncio_cleanup fixture installs an atexit handler that runs BEFORE
Python's logging shutdown. This prevents the "Task was destroyed but it is pending!"
logging error that occurs when:
1. A health monitor task is still pending during Python shutdown
2. The event loop tries to log a warning about the destroyed task
3. But logging file handles are already closed

The atexit handler suppresses asyncio exception logging during final cleanup.
"""

import asyncio
import atexit
import contextlib
from unittest.mock import Mock

import pytest

from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer

# =============================================================================
# Shutdown-Safe Exception Handler
# =============================================================================
#
# The "Task was destroyed but it is pending!" error occurs during Python shutdown
# when:
# 1. An asyncio task is still pending (e.g., health monitor loop)
# 2. The event loop gets garbage collected
# 3. The loop's destructor tries to log a warning about pending tasks
# 4. But logging file handles are already closed
#
# Solution: Patch asyncio's exception handling at a low level to suppress these
# specific errors. We use multiple approaches to ensure coverage:
# 1. Custom exception handler on event loops (may not catch all cases)
# 2. Patched default_exception_handler to catch the logging error
# 3. atexit handler to ensure cleanup runs before Python shutdown
# =============================================================================


def _silent_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """
    Custom asyncio exception handler that silently ignores task destruction messages.

    This handler specifically suppresses the "Task was destroyed but it is pending!"
    warning that occurs during Python shutdown, when logging file handles are already
    closed.

    Args:
        loop: The event loop
        context: Exception context dictionary with 'message', 'exception', etc.
    """
    message = context.get("message", "")
    if "Task was destroyed but it is pending" in message:
        return  # Silently ignore - expected during shutdown

    # For other exceptions, try default behavior but catch logging errors
    try:
        loop.default_exception_handler(context)
    except (ValueError, OSError):
        # "I/O operation on closed file" - logging is already shut down
        pass
    except Exception:
        pass


def _patch_asyncio_exception_handling() -> None:
    """
    Patch asyncio's base event loop to handle logging errors during shutdown.

    This patches the BaseEventLoop.call_exception_handler method to catch
    ValueError from closed logging streams. This is the most reliable way
    to suppress the error because it catches it at the source.
    """
    import asyncio.base_events

    # Store original for potential restoration
    _original_call_exception_handler = (
        asyncio.base_events.BaseEventLoop.call_exception_handler
    )

    def _patched_call_exception_handler(
        self: asyncio.AbstractEventLoop, context: dict
    ) -> None:
        """Patched exception handler that suppresses logging errors during shutdown."""
        try:
            # Check for task destruction message - suppress entirely
            message = context.get("message", "")
            if "Task was destroyed but it is pending" in message:
                return

            # Call original handler
            _original_call_exception_handler(self, context)
        except (ValueError, OSError) as e:
            # "I/O operation on closed file" - logging is shut down
            # This is expected during Python interpreter shutdown
            if "I/O operation on closed file" in str(e):
                pass
            else:
                # Re-raise other ValueError/OSError
                raise
        except Exception:
            # Any other error during exception handling - just ignore
            # We're likely shutting down anyway
            pass

    # Apply the patch
    asyncio.base_events.BaseEventLoop.call_exception_handler = (
        _patched_call_exception_handler
    )


# Apply the patch at module import time
# This ensures ALL event loops (including pytest-asyncio's) use the patched handler
_patch_asyncio_exception_handling()


@pytest.fixture(scope="session", autouse=True)
def final_asyncio_cleanup():
    """
    Session-scoped fixture that ensures proper asyncio cleanup.

    This fixture:
    1. Registers an atexit handler for final task cleanup
    2. Performs cleanup of any remaining tasks at session end
    3. Installs the silent exception handler on the current loop

    The asyncio exception handling is patched at module import time,
    so this fixture primarily handles explicit task cleanup.
    """

    # Register atexit handler for final cleanup
    def _cleanup_at_exit():
        try:
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                # Install silent handler
                loop.set_exception_handler(_silent_exception_handler)

                # Cancel all pending tasks
                try:
                    pending = [
                        task for task in asyncio.all_tasks(loop) if not task.done()
                    ]
                    for task in pending:
                        task.cancel()

                    # Best effort to await cancelled tasks
                    if pending:
                        try:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    atexit.register(_cleanup_at_exit)

    yield

    # Session teardown - do immediate cleanup
    try:
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
            loop.set_exception_handler(_silent_exception_handler)

            try:
                pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if pending:
                    for task in pending:
                        task.cancel()

                    try:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


@pytest.fixture(autouse=True)
def cleanup_pending_tasks():
    """
    Automatically cleanup any pending asyncio tasks after each test.

    This fixture runs after every test in the services directory to ensure
    all health monitoring tasks and service tasks are properly cancelled,
    preventing "Task was destroyed but it is pending!" warnings.

    Suppresses asyncio exception logging during cleanup to prevent noise.
    """
    yield  # Let the test run

    # After test completes, cleanup any pending tasks
    try:
        # Get all pending tasks in the current event loop
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
            # Suppress asyncio exception logging during cleanup
            old_exception_handler = loop.get_exception_handler()
            loop.set_exception_handler(lambda _loop, _context: None)

            try:
                # Get current task to exclude it from cancellation
                try:
                    current_task = asyncio.current_task(loop)
                except RuntimeError:
                    current_task = None

                # Get all tasks except the current one
                pending = [
                    task
                    for task in asyncio.all_tasks(loop)
                    if task is not current_task and not task.done()
                ]

                if pending:
                    # Cancel all pending tasks
                    for task in pending:
                        if not task.done():
                            task.cancel()

                    # Give tasks a moment to process cancellation
                    # Use a short sleep to allow CancelledError to propagate
                    try:
                        loop.run_until_complete(asyncio.sleep(0.1))
                    except Exception:
                        pass

                    # Now gather all the cancelled tasks
                    try:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                    except Exception:
                        # Best effort - some tasks may still be pending
                        pass
            finally:
                # Restore original exception handler
                loop.set_exception_handler(old_exception_handler)

    except RuntimeError:
        # No event loop or loop already closed - this is fine
        pass
    except Exception:
        # Best effort cleanup - don't fail tests due to cleanup issues
        pass


@pytest.fixture
def service_cleanup():
    """
    Fixture to manually register services for cleanup.

    This provides explicit control over service cleanup for tests that
    need it. The cleanup happens automatically via cleanup_pending_tasks,
    but this helper can be used to ensure cleanup happens at specific points.

    Usage:
        @pytest.fixture
        def service_effect(request, mock_container, service_cleanup):
            service = ModelServiceEffect(mock_container)
            service_cleanup.register(service)
            return service
    """
    registered_services = []

    class ServiceCleanupHelper:
        """Helper class to track and cleanup services."""

        def register(self, service):
            """Register a service for automatic cleanup."""
            registered_services.append(service)
            return service

        async def cleanup_service_async(self, service):
            """
            Manually cleanup a specific service (async version).

            Args:
                service: Service instance to cleanup
            """
            # Signal shutdown event first to wake any waiting tasks
            # This is critical for the new event-based shutdown mechanism
            if (
                hasattr(service, "_shutdown_event")
                and service._shutdown_event is not None
            ):
                with contextlib.suppress(Exception):
                    service._shutdown_event.set()

            # Also set shutdown flag to signal the loop to exit
            if hasattr(service, "_shutdown_requested"):
                service._shutdown_requested = True

            # Give health task a moment to wake up and exit cleanly
            if hasattr(service, "_health_task") and service._health_task:
                if isinstance(service._health_task, asyncio.Task):
                    if not service._health_task.done():
                        try:
                            # Wait briefly for clean exit after shutdown event
                            await asyncio.wait_for(service._health_task, timeout=0.3)
                        except TimeoutError:
                            # Task didn't exit in time, cancel it
                            service._health_task.cancel()
                            with contextlib.suppress(asyncio.CancelledError, Exception):
                                await service._health_task
                        except asyncio.CancelledError:
                            # Task was already cancelled, await it to finish cancellation
                            with contextlib.suppress(asyncio.CancelledError, Exception):
                                await service._health_task
                        except Exception:
                            pass

            # Stop service mode if running
            if hasattr(service, "_service_running") and service._service_running:
                with contextlib.suppress(Exception):
                    await service.stop_service_mode()

            # Cancel service task if exists and it's a real task (not a mock)
            if hasattr(service, "_service_task") and service._service_task:
                if isinstance(service._service_task, asyncio.Task):
                    if not service._service_task.done():
                        service._service_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError, Exception):
                            await service._service_task

    helper = ServiceCleanupHelper()

    yield helper

    # Cleanup after test
    async def async_finalizer():
        for service in registered_services:
            await helper.cleanup_service_async(service)

    # Run async finalizer if there are registered services
    if registered_services:
        try:
            loop = asyncio.get_event_loop()
            if loop and not loop.is_closed():
                loop.run_until_complete(async_finalizer())
        except Exception:
            # Best effort - cleanup_pending_tasks will catch remaining tasks
            pass


@pytest.fixture
def mock_container():
    """
    Create mock ModelONEXContainer for dependency injection.

    Provides all required attributes that ModelONEXContainer instances have,
    including compute_cache_config and other container-specific attributes.

    This shared fixture prevents AttributeError: Mock object has no attribute 'compute_cache_config'
    errors across all service tests.
    """
    container = Mock(spec=ModelONEXContainer)

    # Add required ModelONEXContainer attributes
    container.compute_cache_config = ModelComputeCacheConfig()
    container.enable_performance_cache = False
    container.tool_cache = None
    container.performance_monitor = None

    # Add common methods
    container.get_service = Mock(return_value=None)

    return container
