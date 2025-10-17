"""
Shared fixtures for service tests.

Provides cleanup utilities to prevent async task warnings and memory leaks.
"""

import asyncio
import contextlib
from unittest.mock import Mock

import pytest

from omnibase_core.models.configuration.model_compute_cache_config import (
    ModelComputeCacheConfig,
)
from omnibase_core.models.container.model_onex_container import ModelONEXContainer


@pytest.fixture(scope="function", autouse=True)
def cleanup_pending_tasks():
    """
    Automatically cleanup any pending asyncio tasks after each test.

    This fixture runs after every test in the services directory to ensure
    all health monitoring tasks and service tasks are properly cancelled,
    preventing "Task was destroyed but it is pending!" warnings.
    """
    yield  # Let the test run

    # After test completes, cleanup any pending tasks
    try:
        # Get all pending tasks in the current event loop
        loop = asyncio.get_event_loop()
        if loop and not loop.is_closed():
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

                # Wait for all tasks to finish cancellation with timeout
                try:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True),
                            timeout=2.0,
                        )
                    )
                except asyncio.TimeoutError:
                    # Some tasks didn't cancel in time - force them
                    for task in pending:
                        if not task.done():
                            task.cancel()
                            # Try one more time to let them clean up
                            try:
                                loop.run_until_complete(
                                    asyncio.wait({task}, timeout=0.1)
                                )
                            except Exception:
                                pass
    except RuntimeError:
        # No event loop or loop already closed - this is fine
        pass
    except Exception:
        # Best effort cleanup - don't fail tests due to cleanup issues
        pass


@pytest.fixture
def service_cleanup(request):
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
            # Stop service mode if running
            if hasattr(service, "_service_running") and service._service_running:
                with contextlib.suppress(Exception):
                    await service.stop_service_mode()

            # Cancel health task if exists and it's a real task (not a mock)
            if hasattr(service, "_health_task") and service._health_task:
                if isinstance(service._health_task, asyncio.Task):
                    if not service._health_task.done():
                        service._health_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await service._health_task

            # Cancel service task if exists and it's a real task (not a mock)
            if hasattr(service, "_service_task") and service._service_task:
                if isinstance(service._service_task, asyncio.Task):
                    if not service._service_task.done():
                        service._service_task.cancel()
                        with contextlib.suppress(asyncio.CancelledError):
                            await service._service_task

    helper = ServiceCleanupHelper()

    # Register finalizer for explicit cleanup of registered services
    async def async_finalizer():
        for service in registered_services:
            await helper.cleanup_service_async(service)

    def finalizer():
        # Run async finalizer if there are registered services
        if registered_services:
            try:
                loop = asyncio.get_event_loop()
                if loop and not loop.is_closed():
                    loop.run_until_complete(async_finalizer())
            except Exception:
                # Best effort - cleanup_pending_tasks will catch remaining tasks
                pass

    request.addfinalizer(finalizer)

    return helper


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
