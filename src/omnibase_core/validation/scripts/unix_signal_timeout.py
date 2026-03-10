#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Unix-specific timeout handler using SIGALRM."""

from __future__ import annotations

import signal
from collections.abc import Callable
from typing import Any

from omnibase_core.validation.scripts.cross_platform_timeout import CrossPlatformTimeout
from omnibase_core.validation.scripts.timeout_error import TimeoutError  # noqa: A004

__all__ = ["UnixSignalTimeout"]


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
        self.old_handler: signal.Handlers | Callable[[int, Any], Any] | int | None = (
            None
        )
        self.use_signal = hasattr(signal, "SIGALRM")

        # Fallback to threading timeout on Windows
        if not self.use_signal:
            self.fallback_timeout = CrossPlatformTimeout(seconds, error_message)

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Signal handler for SIGALRM."""
        # error-ok: signal handler raises custom TimeoutError
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
