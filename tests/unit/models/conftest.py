# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Conftest for models test suite.

Provides session-level async task cleanup to prevent teardown errors
in large test suites (7,400+ tests).

This complements the per-test cleanup in the root conftest.py by adding
a final cleanup phase that runs after ALL tests in the models directory
complete, ensuring no async tasks remain pending during pytest teardown.
"""

import asyncio
import warnings

import pytest


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    Session cleanup hook for models test suite.

    Runs at the very end of the test session, after all tests complete
    and before pytest's final teardown. Cancels any lingering async tasks
    to prevent "I/O operation on closed file" errors during teardown.

    Why this is needed:
    -------------------
    - Individual test fixtures clean up their own async tasks
    - But in large test suites (7,400+ tests), some tasks from earlier
      tests can linger in the event loop
    - During final pytest teardown, Python tries to log warnings about
      pending tasks, but pytest has already closed log file handles
    - Result: "I/O operation on closed file" and "Task was destroyed
      but it is pending!" errors

    This hook prevents those errors by:
    1. Running at the very end of the session (pytest_sessionfinish hook)
    2. Suppressing asyncio exception logging temporarily
    3. Cancelling all pending tasks in all event loops
    4. Waiting for cancellations to complete with timeout
    5. Forcing cleanup of stubborn tasks

    Related:
    --------
    - Root conftest.py: Per-test cleanup (event_loop_cleanup, cleanup_service_tasks)
    - pyproject.toml: Warning filters for cosmetic asyncio warnings
    - tests/unit/mixins/test_mixin_node_service.py: Health monitor cleanup tests

    Args:
        session: pytest session object
        exitstatus: exit status code
    """
    # Suppress warning output first
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings(
        "ignore", message=".*Task was destroyed but it is pending.*"
    )

    try:
        # Try to get the event loop (not running at this point)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop at all - nothing to clean up
            return

        if not loop or loop.is_closed():
            # No usable event loop
            return

        # Get all pending tasks in this loop
        try:
            all_tasks = asyncio.all_tasks(loop)
        except RuntimeError:
            # all_tasks() can fail if loop is from another thread
            return

        pending_tasks = [task for task in all_tasks if not task.done()]

        if not pending_tasks:
            # No pending tasks - we're good
            return

        # Use print instead of logger since log files may be closed
        print(
            f"\n[Session Cleanup] Found {len(pending_tasks)} pending async tasks, "
            "cancelling...",
            flush=True,
        )

        # Suppress asyncio exception logging during cleanup
        # This prevents "Task was destroyed but it is pending!" warnings
        old_exception_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: None)

        try:
            # Cancel all pending tasks
            for task in pending_tasks:
                if not task.done():
                    task.cancel()

            # Wait for cancellations to complete (with timeout)
            # Use 3 seconds to give health monitors and long-running tasks
            # time to respond to cancellation
            try:

                async def cancel_all():
                    await asyncio.gather(*pending_tasks, return_exceptions=True)

                loop.run_until_complete(asyncio.wait_for(cancel_all(), timeout=3.0))
                print(
                    "[Session Cleanup] All async tasks cancelled successfully",
                    flush=True,
                )
            except TimeoutError:
                # Some tasks didn't cancel in time - force cleanup
                still_pending = [t for t in pending_tasks if not t.done()]
                print(
                    f"[Session Cleanup] WARNING: {len(still_pending)} "
                    "tasks didn't cancel in time, forcing cleanup",
                    flush=True,
                )
                for task in pending_tasks:
                    if not task.done():
                        # Force task to be done by suppressing exception
                        try:
                            task.exception()
                        except (asyncio.CancelledError, asyncio.InvalidStateError):
                            pass
                        except Exception:
                            # Silently ignore exceptions during forced cleanup
                            pass
            except Exception as e:
                # Handle other exceptions during cancellation
                print(
                    f"[Session Cleanup] Exception during task cancellation: {e}",
                    flush=True,
                )

        finally:
            # Restore original exception handler
            loop.set_exception_handler(old_exception_handler)

    except Exception as e:
        # Best effort cleanup - don't fail test suite due to cleanup issues
        # Use print instead of logger since log files may be closed
        print(f"[Session Cleanup] Exception during async cleanup: {e}", flush=True)
