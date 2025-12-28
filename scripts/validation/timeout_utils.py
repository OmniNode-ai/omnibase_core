#!/usr/bin/env python3
"""
Cross-platform timeout utilities for validation scripts.
Provides Windows-compatible timeout handling with proper cleanup.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

# Error message constants for Ruff TRY003 compliance
TIMEOUT_ERROR_MESSAGES = {
    "validation": "Validation operation timed out",
    "file_discovery": "File discovery operation timed out",
    "directory_scan": "Directory scanning operation timed out",
    "file_processing": "File processing operation timed out",
    "general": "Operation timed out",
    "import_validation": "Import validation timed out",
    "type_checking": "Type checking operation timed out",
    "linting": "Code linting operation timed out",
}

# Default timeout values (in seconds)
DEFAULT_TIMEOUTS = {
    "file_discovery": 30,
    "validation": 300,  # 5 minutes
    "directory_scan": 30,
    "import_check": 60,
    "type_check": 120,  # 2 minutes
    "linting": 120,  # 2 minutes
}

T = TypeVar("T")


class TimeoutError(Exception):
    """Cross-platform timeout exception."""


class CrossPlatformTimeout:
    """
    Cross-platform timeout handler using threading.Timer.

    Provides consistent timeout behavior across Windows and Unix systems,
    with proper resource cleanup and cancellation support.
    """

    def __init__(
        self,
        seconds: int,
        error_message: str,
        cleanup_func: Callable[[], None] | None = None,
    ):
        """
        Initialize timeout handler.

        Args:
            seconds: Timeout duration in seconds
            error_message: Error message for timeout exception
            cleanup_func: Optional cleanup function to call on timeout
        """
        self.seconds = seconds
        self.error_message = error_message
        self.cleanup_func = cleanup_func
        self.timer: threading.Timer | None = None
        self.timed_out = False
        self._cancelled = False

    def _timeout_handler(self) -> None:
        """Called when timeout occurs."""
        if self._cancelled:
            return

        self.timed_out = True

        # Run cleanup function if provided
        if self.cleanup_func:
            try:
                self.cleanup_func()
            except Exception as e:
                # Don't let cleanup errors mask the timeout
                print(f"Warning: Timeout cleanup failed: {e}", file=sys.stderr)

    def __enter__(self) -> CrossPlatformTimeout:
        """Start the timeout timer."""
        if self.seconds > 0:
            self.timer = threading.Timer(self.seconds, self._timeout_handler)
            self.timer.daemon = True  # Don't prevent program exit
            self.timer.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cancel timer and check for timeout."""
        self._cancelled = True

        if self.timer:
            self.timer.cancel()
            # Give timer thread a moment to finish
            self.timer.join(timeout=0.1)

        if self.timed_out:
            raise TimeoutError(self.error_message)

    def cancel(self) -> None:
        """Manually cancel the timeout."""
        self._cancelled = True
        if self.timer:
            self.timer.cancel()


class UnixSignalTimeout:
    """
    Unix-specific timeout handler using SIGALRM.

    Only used when signal.SIGALRM is available and explicitly requested.
    Falls back to CrossPlatformTimeout on Windows.
    """

    def __init__(self, seconds: int, error_message: str):
        """Initialize Unix signal timeout."""
        self.seconds = seconds
        self.error_message = error_message
        self.old_handler = None
        self.use_signal = hasattr(signal, "SIGALRM")

        # Fallback to threading timeout on Windows
        if not self.use_signal:
            self.fallback_timeout = CrossPlatformTimeout(seconds, error_message)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Signal handler for SIGALRM."""
        raise TimeoutError(self.error_message)

    def __enter__(self) -> UnixSignalTimeout:
        """Start the timeout."""
        if self.use_signal:
            self.old_handler = signal.signal(signal.SIGALRM, self._signal_handler)
            signal.alarm(self.seconds)
        else:
            self.fallback_timeout.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Cancel timeout and restore signal handler."""
        if self.use_signal:
            signal.alarm(0)  # Cancel alarm
            if self.old_handler is not None:
                signal.signal(signal.SIGALRM, self.old_handler)
        else:
            self.fallback_timeout.__exit__(exc_type, exc_val, exc_tb)


@contextmanager
def timeout_context(
    operation: str,
    duration: int | None = None,
    cleanup_func: Callable[[], None] | None = None,
    use_signal: bool = False,
) -> Generator[None, None, None]:
    """
    Convenient timeout context manager.

    Args:
        operation: Operation type (key in TIMEOUT_ERROR_MESSAGES)
        duration: Timeout duration (uses default if None)
        cleanup_func: Optional cleanup function
        use_signal: Use Unix signals if available (for compatibility)

    Usage:
        with timeout_context("validation", 300):
            # Your validation code here
            validate_files()
    """
    # Get timeout duration and error message
    timeout_seconds = duration or DEFAULT_TIMEOUTS.get(operation, 60)
    error_message = TIMEOUT_ERROR_MESSAGES.get(
        operation, TIMEOUT_ERROR_MESSAGES["general"]
    )

    if use_signal and hasattr(signal, "SIGALRM"):
        with UnixSignalTimeout(timeout_seconds, error_message):
            yield
    else:
        with CrossPlatformTimeout(timeout_seconds, error_message, cleanup_func):
            yield


def with_timeout(
    timeout_seconds: int,
    error_message: str = TIMEOUT_ERROR_MESSAGES["general"],
    cleanup_func: Callable[[], None] | None = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add timeout to any function.

    Args:
        timeout_seconds: Timeout duration
        error_message: Error message for timeout
        cleanup_func: Optional cleanup function

    Usage:
        @with_timeout(60, "File processing timed out")
        def process_files():
            # Your code here
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with CrossPlatformTimeout(timeout_seconds, error_message, cleanup_func):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def create_cleanup_function(files_to_cleanup: list[Path]) -> Callable[[], None]:
    """
    Create a cleanup function that removes temporary files.

    Args:
        files_to_cleanup: List of file paths to clean up

    Returns:
        Cleanup function
    """

    def cleanup() -> None:
        """Clean up temporary files."""
        for file_path in files_to_cleanup:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                print(f"Warning: Failed to cleanup {file_path}: {e}", file=sys.stderr)

    return cleanup


def safe_file_operation(  # noqa: UP047
    file_path: Path,
    operation: Callable[[Path], T],
    timeout_seconds: int = 30,
) -> T:
    """
    Perform a file operation with timeout and error handling.

    Args:
        file_path: Path to the file
        operation: Function that takes a Path and returns result
        timeout_seconds: Timeout for the operation

    Returns:
        Result of the operation

    Raises:
        TimeoutError: If operation times out
        OSError: If file operation fails
    """
    error_message = f"File operation timed out for {file_path}"

    with CrossPlatformTimeout(timeout_seconds, error_message):
        try:
            return operation(file_path)
        except (OSError, PermissionError) as e:
            raise OSError(f"File operation failed for {file_path}: {e}") from e


def get_platform_info() -> dict[str, Any]:
    """
    Get platform information for debugging timeout issues.

    Returns:
        Dictionary with platform information
    """
    return {
        "platform": sys.platform,
        "os_name": os.name,
        "has_sigalrm": hasattr(signal, "SIGALRM"),
        "threading_support": hasattr(threading, "Timer"),
        "python_version": sys.version_info,
    }


# Compatibility aliases for existing code
def setup_timeout_handler() -> None:
    """
    Legacy compatibility function.

    This function does nothing but exists for backward compatibility.
    Use timeout_context() or CrossPlatformTimeout instead.
    """


def cancel_timeout() -> None:
    """
    Legacy compatibility function.

    This function does nothing but exists for backward compatibility.
    Use context managers for proper timeout cancellation.
    """


if __name__ == "__main__":
    # Test the timeout functionality
    print("Testing cross-platform timeout utilities...")

    # Test platform info
    platform_info = get_platform_info()
    print(f"Platform info: {platform_info}")

    # Test short timeout
    try:
        with timeout_context("general", 1):
            print("Starting 2-second sleep (should timeout)...")
            time.sleep(2)
        print("ERROR: Should have timed out!")
    except TimeoutError as e:
        print(f"✅ Timeout worked correctly: {e}")

    # Test normal operation
    try:
        with timeout_context("general", 2):
            print("Starting 1-second sleep (should complete)...")
            time.sleep(1)
        print("✅ Normal operation completed successfully")
    except TimeoutError:
        print("ERROR: Should not have timed out!")

    print("Timeout utility tests completed.")
