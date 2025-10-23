"""
Root conftest.py for test suite.

Provides memory optimization, resource cleanup, and shared fixtures
to prevent OOM issues in large test suites.
"""

import asyncio
import gc
import logging
from typing import Generator

import pytest

# Configure logging to reduce memory overhead
logging.basicConfig(level=logging.WARNING)


@pytest.fixture(scope="session", autouse=True)
def session_cleanup() -> Generator[None, None, None]:
    """
    Session-level cleanup to manage memory across entire test run.

    This fixture runs once at the start and end of the test session,
    providing global cleanup and garbage collection.
    """
    # Session setup
    gc.collect()  # Clean up before starting tests
    yield

    # Session teardown
    gc.collect()  # Clean up after all tests complete


@pytest.fixture(autouse=True)
def aggressive_gc_cleanup() -> Generator[None, None, None]:
    """
    Aggressive garbage collection after each test.

    This fixture runs after every test to immediately free memory,
    preventing accumulation across thousands of tests.
    """
    yield  # Let test run

    # Force garbage collection after test completes
    gc.collect()


@pytest.fixture(autouse=True)
def event_loop_cleanup() -> Generator[None, None, None]:
    """
    Clean up event loops and async tasks after each test.

    Ensures no dangling event loops or tasks that could accumulate memory.
    Specifically handles health monitor tasks that may have long sleep intervals.
    """
    yield  # Let test run

    # Clean up any remaining event loops
    try:
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, try to get the event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop at all - that's fine
                return

        if loop and not loop.is_closed():
            # Get all pending tasks in this loop
            try:
                pending = asyncio.all_tasks(loop)
            except RuntimeError:
                # asyncio.all_tasks() can fail if loop is from another thread
                return

            if pending:
                # Cancel all pending tasks
                for task in pending:
                    if not task.done():
                        task.cancel()

                # Give tasks up to 2 seconds to complete cancellation
                # This is important for health monitor tasks with sleep intervals
                try:
                    # Use wait_for with timeout to prevent hanging
                    async def cancel_all():
                        await asyncio.gather(*pending, return_exceptions=True)

                    loop.run_until_complete(asyncio.wait_for(cancel_all(), timeout=2.0))
                except asyncio.TimeoutError:
                    # Some tasks didn't cancel in time - force cleanup
                    for task in pending:
                        if not task.done():
                            # Force task to be done by suppressing exception
                            try:
                                task.exception()
                            except (asyncio.CancelledError, asyncio.InvalidStateError):
                                pass
                except Exception:
                    # Best effort cleanup - don't fail tests due to cleanup issues
                    pass

    except RuntimeError:
        # Event loop issues - that's fine, just skip cleanup
        pass


@pytest.fixture(scope="session")
def memory_profiler_enabled() -> bool:
    """
    Check if memory profiling is enabled.

    Set PYTEST_MEMORY_PROFILE=1 environment variable to enable.
    """
    import os

    return os.environ.get("PYTEST_MEMORY_PROFILE", "0") == "1"


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure pytest with memory optimization settings.

    Args:
        config: pytest configuration object
    """
    # Register custom markers
    config.addinivalue_line(
        "markers",
        "memory_intensive: mark test as memory intensive (may need sequential execution)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """
    Modify test collection to optimize memory usage.

    Args:
        config: pytest configuration object
        items: list of collected test items
    """
    # Sort tests to group related tests together (better cache locality)
    items.sort(key=lambda item: (item.module.__name__, item.name))


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """
    Run before each test to prepare environment.

    Args:
        item: pytest test item
    """
    # Force garbage collection before memory-intensive tests
    if item.get_closest_marker("memory_intensive"):
        gc.collect()


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    """
    Run after each test to clean up resources.

    Args:
        item: pytest test item
        nextitem: next test item (None if last test)
    """
    # Force garbage collection after memory-intensive tests
    if item.get_closest_marker("memory_intensive"):
        gc.collect()

    # If next test is in different module, force GC to free module memory
    if nextitem and nextitem.module != item.module:
        gc.collect()


@pytest.fixture(autouse=True)
async def cleanup_service_tasks() -> Generator[None, None, None]:
    """
    Specifically clean up service-related async tasks after each test.

    This fixture targets health monitor tasks and service loops that may
    be created during service testing and not properly cleaned up.
    """
    yield  # Let test run

    # Give any pending cleanup a moment to complete
    await asyncio.sleep(0.1)

    # Force cleanup of any remaining tasks
    try:
        # Get current event loop if available
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return  # No running loop

        # Get all tasks
        all_tasks = asyncio.all_tasks(loop)

        # Filter for health monitor and service tasks
        health_tasks = [
            task
            for task in all_tasks
            if not task.done()
            and (
                "_health_monitor_loop" in str(task.get_coro())
                or "_service_loop" in str(task.get_coro())
            )
        ]

        if health_tasks:
            # Cancel health monitor tasks specifically
            for task in health_tasks:
                task.cancel()

            # Wait for cancellation with timeout
            try:
                await asyncio.wait_for(
                    asyncio.gather(*health_tasks, return_exceptions=True),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                # Tasks didn't cancel in time - they'll be cleaned up by event_loop_cleanup
                pass

    except Exception:
        # Best effort cleanup - don't fail tests
        pass


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Run after entire test session completes.

    Args:
        session: pytest session object
        exitstatus: exit status code
    """
    # Final cleanup
    gc.collect()

    # Log memory statistics if profiling enabled
    try:
        import os

        if os.environ.get("PYTEST_MEMORY_PROFILE", "0") == "1":
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()
            print(f"\n=== Test Suite Memory Statistics ===")
            print(f"RSS (Resident Set Size): {memory_info.rss / 1024 / 1024:.2f} MB")
            print(f"VMS (Virtual Memory Size): {memory_info.vms / 1024 / 1024:.2f} MB")
    except ImportError:
        pass  # psutil not available - skip memory profiling
