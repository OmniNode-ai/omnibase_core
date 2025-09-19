"""
Backpressure strategy enum for streaming configurations.
"""

from enum import Enum


class EnumBackpressureStrategy(str, Enum):
    """Supported backpressure handling strategies for streaming."""

    BUFFER = "buffer"
    DROP = "drop"
    BLOCK = "block"
    THROTTLE = "throttle"
    REJECT = "reject"
    SPILL_TO_DISK = "spill_to_disk"
