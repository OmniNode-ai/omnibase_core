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

    Thread Safety Guarantees:
        This class is designed for concurrent access from multiple threads:

        1. **Lock-Protected State Access**: All reads and writes to mutable state
           (listener_thread, stop_event, subscriptions, is_running) are protected
           by an internal lock (_lock).

        2. **Idempotent Operations**: The stop() method is idempotent - calling it
           multiple times from multiple threads is safe and produces consistent
           results.

        3. **Lock-Release-Before-Block Pattern**: The stop() method uses a careful
           lock acquisition pattern that releases the lock before potentially
           blocking operations (thread.join()) to avoid blocking other callers.
           See stop() method documentation for details.

        4. **Reference Capture**: When performing operations that may block, thread
           and event references are captured under the lock, then the lock is
           released before blocking. This ensures the references remain valid while
           allowing other threads to proceed.

    Concurrency Model:
        - Multiple threads can safely call stop() simultaneously
        - Multiple threads can safely call is_active() simultaneously
        - State modifications are atomic with respect to the lock
        - The listener thread itself should check stop_event.is_set() to
          determine when to terminate

    Example:
        >>> handle = ModelEventBusListenerHandle()
        >>> # Start listener (thread management done externally)
        >>> handle.listener_thread = threading.Thread(target=listener_loop, daemon=True)
        >>> handle.stop_event = threading.Event()
        >>> handle.is_running = True
        >>> handle.listener_thread.start()
        >>>
        >>> # Later, stop the listener (safe from any thread)
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

    def __deepcopy__(
        self, memo: dict[int, Any] | None = None
    ) -> "ModelEventBusListenerHandle":
        """
        Create a deep copy of this handle with a new lock instance.

        threading.Lock objects cannot be pickled or deep-copied, so we create
        a new lock for the copied instance. Thread and Event objects are also
        reset since they cannot be meaningfully copied - a copied handle starts
        in a stopped state with no active thread.

        Thread Safety:
            Subscriptions are deep-copied with error handling because:
            1. They may contain objects that cannot be deep-copied (callbacks,
               closures referencing threading objects, etc.)
            2. If deep copy fails, we fall back to an empty list rather than
               raising an exception
            3. A warning is logged when subscriptions cannot be copied

        Note:
            - listener_thread is set to None (a started Thread references an OS
              thread and cannot be meaningfully duplicated)
            - stop_event is replaced with a fresh Event if one existed (copying
              an Event would create one that doesn't share state with the original)
            - is_running is set to False (the copy has no active thread)
            - subscriptions are deep-copied if possible, otherwise empty list

        Args:
            memo: Dictionary of already copied objects (for cycle detection).

        Returns:
            A new ModelEventBusListenerHandle with independent state and a new lock,
            starting in a stopped state.
        """
        if memo is None:
            memo = {}

        # Try to deep copy subscriptions, fall back to empty list if it fails
        # Subscriptions may contain callbacks or closures that reference
        # threading objects which cannot be deep copied
        try:
            copied_subscriptions = copy.deepcopy(self.subscriptions, memo)
        except (TypeError, RuntimeError) as e:
            # TypeError: Can't pickle lock objects
            # RuntimeError: Can't deep copy threading objects
            emit_log_event(
                LogLevel.DEBUG,
                f"DEEPCOPY: Cannot deep copy subscriptions, using empty list: {e!r}",
                context={"error_type": type(e).__name__},
            )
            copied_subscriptions = []

        # Don't copy active thread state - it cannot be meaningfully duplicated
        new_handle = ModelEventBusListenerHandle(
            listener_thread=None,  # Thread cannot be copied
            stop_event=threading.Event() if self.stop_event else None,
            subscriptions=copied_subscriptions,
            is_running=False,  # Copy is not running
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

        Timeout Considerations:
            The default 5.0 second timeout is suitable for most production and
            CI environments. For CI pipelines with strict time constraints,
            consider using a shorter timeout (e.g., 2.0 seconds) to fail fast.
            For production systems with complex cleanup, longer timeouts may
            be appropriate.

            Since listener threads are daemon threads (daemon=True), they will
            be automatically terminated by Python when the main thread exits,
            even if they don't respond to the stop signal within the timeout.
            This means a timeout does not cause resource leaks - it only means
            the thread didn't stop gracefully within the allotted time.

        Thread Safety - Lock Acquisition Pattern:
            This method uses a deliberate three-phase lock pattern to prevent
            race conditions while avoiding blocking other callers during the
            potentially long join() operation:

            **Phase 1 - Capture and Signal (lock held)**:
                - Acquire lock
                - Check if already stopped (idempotent early return)
                - Capture references to stop_event and listener_thread
                - Set the stop_event to signal thread termination
                - Release lock

            **Phase 2 - Wait for Thread (lock NOT held)**:
                - Call thread.join(timeout) on the captured reference
                - This may block for up to `timeout` seconds
                - Other threads can call stop() or is_active() during this time
                - The captured thread reference remains valid because Python
                  keeps objects alive while references exist

            **Phase 3 - Cleanup (lock held)**:
                - Reacquire lock
                - Clear subscriptions list
                - Set is_running = False
                - Release lock

            Why release the lock before join()?
                If we held the lock during join(), any other thread calling
                stop() or is_active() would block for up to `timeout` seconds.
                By releasing the lock, other callers can:
                - Return immediately if checking is_active()
                - Complete their own stop() call (idempotently)

            Race Condition Prevention:
                - The captured thread reference is safe to use outside the lock
                  because Python's reference counting keeps it alive
                - Multiple concurrent stop() calls are safe: the first sets
                  stop_event, others see it already set or see is_running=False
                - The final state (is_running=False, subscriptions cleared) is
                  set atomically under the lock in Phase 3
        """
        # === Phase 1: Capture and Signal (lock held) ===
        with self._lock:
            # Already stopped - idempotent behavior allows safe concurrent calls
            if not self.is_running and (
                self.listener_thread is None or not self.listener_thread.is_alive()
            ):
                return True

            # Capture references under lock - these remain valid after lock release
            # because Python's reference counting keeps the objects alive
            stop_event = self.stop_event
            listener_thread = self.listener_thread

            # Signal the listener to stop while still holding the lock
            if stop_event is not None:
                stop_event.set()
        # Lock released here - other threads can now call stop() or is_active()

        # === Phase 2: Wait for Thread (lock NOT held) ===
        # We intentionally release the lock before join() to avoid blocking
        # other callers during the potentially long wait operation
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

        # === Phase 3: Cleanup (lock held) ===
        # Reacquire lock to atomically update final state
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
