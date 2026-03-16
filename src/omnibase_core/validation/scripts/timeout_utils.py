#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Cross-platform timeout utilities for validation scripts.
Provides Windows-compatible timeout handling with proper cleanup.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TypeVar

from omnibase_core.validation.scripts.cross_platform_timeout import CrossPlatformTimeout
from omnibase_core.validation.scripts.timeout_error import TimeoutError  # noqa: A004
from omnibase_core.validation.scripts.unix_signal_timeout import UnixSignalTimeout

__all__ = [
    "CrossPlatformTimeout",
    "TimeoutError",
    "UnixSignalTimeout",
    "TIMEOUT_ERROR_MESSAGES",
    "DEFAULT_TIMEOUTS",
    "timeout_context",
    "with_timeout",
    "create_cleanup_function",
    "safe_file_operation",
    "get_platform_info",
]

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
        use_signal: Use Unix signals if available (prefers signal-based timeout on Unix)

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
            except Exception as e:  # noqa: BLE001
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
            raise OSError(  # error-ok: re-raising standard OS exception at utility boundary
                f"File operation failed for {file_path}: {e}"
            ) from e


def get_platform_info() -> dict[str, Any]:  # ONEX_EXCLUDE: dict_str_any
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


if __name__ == "__main__":
    # Test the timeout functionality
    import time

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
