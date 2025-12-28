# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
Event bus listener handle for managing listener lifecycle.

This model encapsulates the runtime state for event bus listeners, including
thread management, stop signals, and subscription tracking. All fields are
excluded from serialization as this is purely a runtime management object.
"""

import copy
import threading
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from omnibase_core.enums.enum_log_level import EnumLogLevel as LogLevel
from omnibase_core.logging.structured import emit_log_event_sync as emit_log_event


class ModelEventBusListenerHandle(BaseModel):
    """
    Handle for managing event bus listener lifecycle.

    This model manages the runtime state of an event bus listener, including:
    - Background thread for event processing
    - Stop signal for graceful shutdown
    - Active subscription tracking
    - Running state management

    All fields are excluded from serialization as this is a runtime-only object
    that should not be persisted or transmitted.

    Thread Safety:
        The stop() and is_active() methods are thread-safe and can be called
        from multiple threads simultaneously. Internal state is protected by
        a lock to prevent race conditions.

    Example:
        >>> handle = ModelEventBusListenerHandle()
        >>> # Start listener (thread management done externally)
        >>> handle.listener_thread = threading.Thread(target=listener_loop, daemon=True)
        >>> handle.stop_event = threading.Event()
        >>> handle.is_running = True
        >>> handle.listener_thread.start()
        >>>
        >>> # Later, stop the listener
        >>> success = handle.stop(timeout=5.0)
        >>> if not success:
        ...     print("Warning: listener did not stop within timeout")
    """

    model_config = ConfigDict(
        frozen=False,
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    # Private lock for thread-safe state access (not serialized)
    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)

    listener_thread: threading.Thread | None = Field(
        default=None,
        exclude=True,
        description="Background thread running the event listener loop.",
    )

    stop_event: threading.Event | None = Field(
        default=None,
        exclude=True,
        description="Threading event used to signal the listener to stop.",
    )

    subscriptions: list[Any] = Field(
        default_factory=list,
        exclude=True,
        description="List of active event subscriptions managed by this listener.",
    )

    is_running: bool = Field(
        default=False,
        exclude=True,
        description="Whether the listener is currently running.",
    )

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> "ModelEventBusListenerHandle":
        """
        Create a deep copy of this handle with a new lock instance.

        threading.Lock objects cannot be pickled or deep-copied, so we create
        a new lock for the copied instance. Other fields are deep-copied normally.

        Args:
            memo: Dictionary of already copied objects (for cycle detection).

        Returns:
            A new ModelEventBusListenerHandle with independent state and a new lock.
        """
        if memo is None:
            memo = {}

        # Create a new instance with a fresh lock
        new_handle = ModelEventBusListenerHandle(
            listener_thread=copy.deepcopy(self.listener_thread, memo),
            stop_event=copy.deepcopy(self.stop_event, memo),
            subscriptions=copy.deepcopy(self.subscriptions, memo),
            is_running=self.is_running,
        )
        memo[id(self)] = new_handle
        return new_handle

    def stop(self, timeout: float = 5.0) -> bool:
        """
        Stop the listener with a bounded timeout.

        This method is idempotent and thread-safe - calling it multiple times
        from multiple threads is safe and will return True if the listener is
        already stopped.

        Args:
            timeout: Maximum time in seconds to wait for the listener thread
                to stop. Defaults to 5.0 seconds.

        Returns:
            True if the listener was successfully stopped or was already stopped.
            False if the listener thread did not stop within the timeout.

        Note:
            - Sets the stop_event to signal the listener thread to terminate
            - Waits up to `timeout` seconds for the thread to join
            - Logs a warning if the thread does not stop within the timeout
            - Clears subscriptions and resets is_running state regardless of
              whether the thread stopped

        Thread Safety:
            This method is protected by a lock to prevent race conditions when
            multiple threads call stop() simultaneously.
        """
        with self._lock:
            # Already stopped - idempotent behavior
            if not self.is_running and (
                self.listener_thread is None or not self.listener_thread.is_alive()
            ):
                return True

            # Capture references under lock before potentially blocking operations
            stop_event = self.stop_event
            listener_thread = self.listener_thread

            # Signal the listener to stop (while holding lock)
            if stop_event is not None:
                stop_event.set()

        # Wait for thread to finish OUTSIDE the lock to avoid blocking other
        # callers during the potentially long join operation
        thread_stopped = True
        if listener_thread is not None and listener_thread.is_alive():
            listener_thread.join(timeout=timeout)

            if listener_thread.is_alive():
                # Thread did not stop within timeout
                thread_stopped = False
                emit_log_event(
                    LogLevel.WARNING,
                    f"Listener thread did not stop within {timeout}s timeout",
                    context={
                        "thread_name": listener_thread.name,
                        "timeout_seconds": timeout,
                    },
                )

        # Clear state under lock
        with self._lock:
            self.subscriptions.clear()
            self.is_running = False

        return thread_stopped

    def is_active(self) -> bool:
        """
        Check if the listener thread is currently alive.

        Returns:
            True if the listener thread exists and is alive, False otherwise.

        Note:
            This checks the actual thread state, not just the is_running flag.
            A listener may have is_running=True but is_active()=False if the
            thread terminated unexpectedly.

        Thread Safety:
            This method is protected by a lock to ensure consistent reads of
            the listener_thread reference.
        """
        with self._lock:
            listener_thread = self.listener_thread
        # Check is_alive() outside lock since it's a read-only operation on
        # the thread object itself (which is thread-safe)
        return listener_thread is not None and listener_thread.is_alive()
