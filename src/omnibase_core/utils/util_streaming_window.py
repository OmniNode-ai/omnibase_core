"""
Streaming window utility for time-based data processing.

This module provides the UtilStreamingWindow class that implements
time-based windowing for streaming data reduction operations. Windows
can optionally overlap for sliding window semantics.

Thread Safety:
    UtilStreamingWindow is NOT thread-safe. The internal buffer is
    mutated during add_item() and advance_window() operations. Each
    thread should use its own instance.

Key Features:
    - Time-based window duration (configurable in milliseconds)
    - Optional overlap for sliding window patterns
    - Automatic window completion detection
    - Efficient deque-based buffer implementation

Example:
    >>> from omnibase_core.utils.util_streaming_window import UtilStreamingWindow
    >>>
    >>> # 5-second tumbling window (no overlap)
    >>> window = UtilStreamingWindow(window_size_ms=5000)
    >>> for event in event_stream:
    ...     is_ready = window.add_item(event)
    ...     if is_ready:
    ...         items = window.get_window_items()
    ...         process_batch(items)
    ...         window.advance_window()
    >>>
    >>> # 10-second sliding window with 2-second overlap
    >>> sliding_window = UtilStreamingWindow(
    ...     window_size_ms=10000,
    ...     overlap_ms=2000,
    ... )

See Also:
    - omnibase_core.models.reducer.model_reducer_input: Uses streaming windows
    - omnibase_core.enums.enum_reducer_types.EnumStreamingMode: Streaming modes
"""

from collections import deque
from datetime import datetime, timedelta


class UtilStreamingWindow:
    """
    Time-based window for streaming data processing.

    Provides time-based windowing with optional overlap for streaming
    reduction operations. Items are buffered with timestamps and the
    window automatically tracks when it's ready for processing.

    Attributes:
        window_size_ms: Duration of the window in milliseconds.
        overlap_ms: Overlap duration for sliding windows. When > 0, items
            within the overlap period are retained after advancing.
        buffer: Internal deque storing (item, timestamp) tuples.
        window_start: Timestamp when current window started.

    Window Types:
        - Tumbling Window: overlap_ms=0 (default). Windows are non-overlapping
          and each item belongs to exactly one window.
        - Sliding Window: overlap_ms>0. Windows overlap and items may be
          processed in multiple consecutive windows.

    Thread Safety:
        UtilStreamingWindow is NOT thread-safe. It maintains mutable internal
        state (buffer deque and window_start timestamp) that is modified during
        add_item() and advance_window() operations without synchronization.
        Use separate instances per thread or wrap access with external locks.

    .. note::
        Previously named ``ModelStreamingWindow``. Renamed in v0.4.0
        to follow ONEX naming conventions (OMN-1071). The ``Model``
        prefix is reserved for Pydantic BaseModel classes; ``Util``
        prefix indicates a utility class.
    """

    def __init__(self, window_size_ms: int, overlap_ms: int = 0):
        """
        Initialize streaming window.

        Args:
            window_size_ms: Window size in milliseconds
            overlap_ms: Overlap size in milliseconds (default: 0)
        """
        self.window_size_ms = window_size_ms
        self.overlap_ms = overlap_ms
        self.buffer: deque[tuple[object, datetime]] = deque()
        self.window_start = datetime.now()

    def add_item(self, item: object) -> bool:
        """
        Add item to window.

        Args:
            item: Item to add to window

        Returns:
            True if window is full and ready to process
        """
        current_time = datetime.now()
        self.buffer.append((item, current_time))

        # Check if window is complete
        window_duration = (current_time - self.window_start).total_seconds() * 1000
        return window_duration >= self.window_size_ms

    def get_window_items(self) -> list[object]:
        """
        Get all items in current window.

        Returns:
            List of items in current window
        """
        return [item for item, _timestamp in self.buffer]

    def advance_window(self) -> None:
        """Advance to next window with optional overlap."""
        if self.overlap_ms > 0:
            # Keep overlapping items
            cutoff_time = self.window_start + timedelta(
                milliseconds=self.window_size_ms - self.overlap_ms,
            )
            self.buffer = deque(
                [
                    (item, timestamp)
                    for item, timestamp in self.buffer
                    if timestamp >= cutoff_time
                ],
            )
        else:
            # Clear all items
            self.buffer.clear()

        self.window_start = datetime.now()


def __getattr__(name: str) -> object:
    """
    Lazy loading for deprecated aliases per OMN-1071 renaming.

    Deprecated Aliases:
    -------------------
    All deprecated aliases emit DeprecationWarning when accessed:
    - ModelStreamingWindow -> UtilStreamingWindow
    """
    import warnings

    if name == "ModelStreamingWindow":
        warnings.warn(
            "'ModelStreamingWindow' is deprecated, use 'UtilStreamingWindow' "
            "from 'omnibase_core.utils.util_streaming_window' instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return UtilStreamingWindow

    raise AttributeError(  # error-ok: required for __getattr__ protocol
        f"module {__name__!r} has no attribute {name!r}"
    )
