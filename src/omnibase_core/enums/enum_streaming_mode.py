"""Streaming mode enumeration for data processing strategies."""

from enum import Enum, unique


@unique
class EnumStreamingMode(Enum):
    """Streaming processing modes."""

    BATCH = "batch"  # Process all data at once
    INCREMENTAL = "incremental"  # Process data incrementally
    WINDOWED = "windowed"  # Process in time windows
    REAL_TIME = "real_time"  # Process as data arrives
