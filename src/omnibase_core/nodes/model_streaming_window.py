"""
Streaming window model for time-based data processing.

Implements time-based windowing for streaming data reduction operations.

Author: ONEX Framework Team
"""

from collections import deque
from datetime import datetime, timedelta
from typing import Any


class ModelStreamingWindow:
    """
    Time-based window for streaming data processing.

    Provides time-based windowing with optional overlap for streaming
    reduction operations.
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
        self.buffer: deque[tuple[Any, datetime]] = deque()
        self.window_start = datetime.now()

    def add_item(self, item: Any) -> bool:
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

    def get_window_items(self) -> list[Any]:
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
