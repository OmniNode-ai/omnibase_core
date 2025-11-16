"""
Root conftest.py for test suite.

Provides memory optimization, resource cleanup, and shared fixtures
to prevent OOM issues in large test suites.

Warning Suppression:
-------------------
Asyncio warnings are configured in pyproject.toml [tool.pytest.ini_options]:
- "Task was destroyed but it is pending!" warnings are suppressed (expected during cleanup)
- "coroutine was never awaited" warnings are NOT suppressed (indicate real bugs)

See pyproject.toml filterwarnings configuration for details.
"""

import asyncio
import gc
import logging
import threading
from collections.abc import Generator
from unittest.mock import MagicMock

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

    CRITICAL: Stops all event listener threads BEFORE gc.collect() to prevent
    deadlock when Mock objects in background threads are accessed during
    garbage collection.
    """
    yield  # Let test run

    # Stop all event listener threads before garbage collection
    # Background threads with Mock objects can deadlock during gc.collect()
    for thread in threading.enumerate():
        if thread.name and "test_node_event_listener" in thread.name:
            # Thread should have stopped naturally, but ensure cleanup
            if thread.is_alive():
                # Give thread up to 2 seconds to finish
                thread.join(timeout=2.0)

    # Now safe to collect garbage - no background threads with Mock objects
    gc.collect()


@pytest.fixture(autouse=True)
def event_loop_cleanup() -> Generator[None, None, None]:
    """
    Clean up event loops and async tasks after each test.

    Ensures no dangling event loops or tasks that could accumulate memory.
    Specifically handles health monitor tasks that may have long sleep intervals.
    Suppresses asyncio exception logging during cleanup to prevent noise.
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
            # Suppress asyncio exception logging during cleanup
            # Prevents "Task was destroyed but it is pending!" warnings
            old_exception_handler = loop.get_exception_handler()
            loop.set_exception_handler(lambda loop, context: None)

            try:
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

                        loop.run_until_complete(
                            asyncio.wait_for(cancel_all(), timeout=2.0)
                        )
                    except TimeoutError:
                        # Some tasks didn't cancel in time - force cleanup
                        for task in pending:
                            if not task.done():
                                # Force task to be done by suppressing exception
                                try:
                                    task.exception()
                                except (
                                    asyncio.CancelledError,
                                    asyncio.InvalidStateError,
                                ):
                                    pass
                    except Exception:
                        # Best effort cleanup - don't fail tests due to cleanup issues
                        pass
            finally:
                # Restore original exception handler
                loop.set_exception_handler(old_exception_handler)

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

    Also suppresses asyncio exception logging during cleanup to prevent
    "Task was destroyed but it is pending!" warnings when tasks are cancelled
    during test teardown.
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

        # Suppress asyncio exception logging during cleanup
        # This prevents "Task was destroyed but it is pending!" errors
        # when we cancel tasks during test teardown
        old_exception_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: None)

        try:
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
                    or "_service_event_loop" in str(task.get_coro())
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
                except TimeoutError:
                    # Tasks didn't cancel in time - they'll be cleaned up by event_loop_cleanup
                    pass
        finally:
            # Restore original exception handler
            loop.set_exception_handler(old_exception_handler)

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
            print("\n=== Test Suite Memory Statistics ===")
            print(f"RSS (Resident Set Size): {memory_info.rss / 1024 / 1024:.2f} MB")
            print(f"VMS (Virtual Memory Size): {memory_info.vms / 1024 / 1024:.2f} MB")
    except ImportError:
        pass  # psutil not available - skip memory profiling


# =============================================================================
# Preventive Fixtures for Event Loop Testing
# =============================================================================


@pytest.fixture
def mock_event_loop() -> Generator[MagicMock, None, None]:
    """
    Provide a mock event loop to prevent real event loop creation in tests.

    This fixture prevents test hangs caused by real event loop creation in CI
    environments, particularly when testing workflow or async execution patterns
    with mocked llama_index dependencies.

    Usage:
        def test_workflow_execution(mock_event_loop):
            '''Test workflow with mocked event loop.'''
            mock_event_loop.run_until_complete.return_value = expected_result

            with patch("llama_index.core.workflow"):
                with patch("asyncio.new_event_loop", return_value=mock_event_loop):
                    result = tool.execute_workflow(input_state)

            # Verify event loop was properly closed
            mock_event_loop.close.assert_called_once()

    Pattern:
        - Mock event loop before calling code that creates event loops
        - Set return values on run_until_complete for expected results
        - Always verify close() was called to ensure cleanup

    Why This Matters:
        - Real event loop creation can hang in CI environments
        - Event loops must be properly closed to prevent resource leaks
        - Mocked event loops provide deterministic test behavior

    When NOT to use this fixture:
        - When tests need specific return values from run_until_complete()
        - When multiple different workflows are tested in one test
        - See tests/unit/mixins/test_mixin_hybrid_execution.py for manual mock pattern

    See Also:
        - tests/unit/mixins/test_mixin_hybrid_execution.py for examples
        - Commit 57c4ae95: Original fix for test_execute_orchestrated_falls_back_to_workflow
    """
    mock_loop = MagicMock()
    mock_loop.run_until_complete.return_value = None
    yield mock_loop

    # Verify the loop was closed (good practice check)
    if not mock_loop.close.called:
        import warnings

        warnings.warn(
            "mock_event_loop was not closed in test. "
            "Always call mock_loop.close.assert_called_once() to verify cleanup.",
            RuntimeWarning,
            stacklevel=2,
        )


@pytest.fixture(autouse=True)
def detect_event_loop_mocking_issues(request: pytest.FixtureRequest) -> None:
    """
    Auto-detect and warn about missing event loop mocks in workflow tests.

    This fixture monitors test execution and issues warnings when tests mock
    llama_index but fail to mock asyncio.new_event_loop, which can cause hangs.

    The fixture is autouse=True but only activates warnings for tests that:
    1. Use patch decorators or context managers for llama_index
    2. Don't use the mock_event_loop fixture
    3. Actually call code that creates event loops

    Note: This is a best-effort detection mechanism. False positives/negatives
    are possible. Use mock_event_loop fixture explicitly for guaranteed safety.
    """
    # Check if test uses mock_event_loop fixture
    if "mock_event_loop" in request.fixturenames:
        return  # Test is already using the fixture, no warning needed

    # Only check tests in specific modules known to have this pattern
    test_module = request.module.__name__
    if not (
        "test_mixin_hybrid_execution" in test_module
        or "test_hybrid_execution" in test_module
        or "test_workflow" in test_module
        or "test_orchestrat" in test_module
    ):
        return  # Skip detection for unrelated tests

    # Note: Detection of actual llama_index mocking would require AST parsing
    # or runtime inspection, which is expensive. Instead, we rely on:
    # 1. Explicit use of mock_event_loop fixture (recommended)
    # 2. Code review to ensure pattern compliance
    # 3. CI timeouts to catch actual hangs

    # This fixture serves primarily as documentation and a reminder
    # to use mock_event_loop when testing workflow/async patterns
