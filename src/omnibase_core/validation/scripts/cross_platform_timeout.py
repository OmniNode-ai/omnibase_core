#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Cross-platform timeout handler using threading.Timer."""

from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from typing import Any

from omnibase_core.validation.scripts.timeout_error import TimeoutError  # noqa: A004

__all__ = ["CrossPlatformTimeout"]


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
            # error-ok: cross-platform timeout utility raises custom TimeoutError
            raise TimeoutError(self.error_message)

    def cancel(self) -> None:
        """Manually cancel the timeout."""
        self._cancelled = True
        if self.timer:
            self.timer.cancel()
