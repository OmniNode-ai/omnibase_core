"""
Memory Usage Enumeration.

Defines categories for memory usage levels.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumMemoryUsage(StrValueHelper, str, Enum):
    """
    Memory usage enumeration.

    Represents different levels of memory consumption for operations.
    """

    # Minimal memory usage
    MINIMAL = "minimal"  # < 10 MB
    TINY = "tiny"  # 10-50 MB
    SMALL = "small"  # 50-100 MB

    # Moderate memory usage
    LOW = "low"  # 100-250 MB
    MODERATE = "moderate"  # 250-500 MB
    MEDIUM = "medium"  # 500 MB - 1 GB

    # Higher memory usage
    HIGH = "high"  # 1-2 GB
    LARGE = "large"  # 2-4 GB
    VERY_HIGH = "very_high"  # 4-8 GB

    # Extreme memory usage
    EXTREME = "extreme"  # 8-16 GB
    MASSIVE = "massive"  # 16+ GB
    UNLIMITED = "unlimited"  # No specific limit

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()

    @property
    def estimated_mb(self) -> tuple[float, float | None]:
        """Get estimated memory range in megabytes."""
        ranges: dict[EnumMemoryUsage, tuple[float, float | None]] = {
            EnumMemoryUsage.MINIMAL: (0, 10),
            EnumMemoryUsage.TINY: (10, 50),
            EnumMemoryUsage.SMALL: (50, 100),
            EnumMemoryUsage.LOW: (100, 250),
            EnumMemoryUsage.MODERATE: (250, 500),
            EnumMemoryUsage.MEDIUM: (500, 1024),
            EnumMemoryUsage.HIGH: (1024, 2048),
            EnumMemoryUsage.LARGE: (2048, 4096),
            EnumMemoryUsage.VERY_HIGH: (4096, 8192),
            EnumMemoryUsage.EXTREME: (8192, 16384),
            EnumMemoryUsage.MASSIVE: (16384, None),
            EnumMemoryUsage.UNLIMITED: (0, None),
        }
        return ranges.get(self, (0, None))

    @property
    def estimated_gb(self) -> tuple[float, float | None]:
        """Get estimated memory range in gigabytes."""
        mb_range = self.estimated_mb
        min_gb = mb_range[0] / 1024
        max_gb = mb_range[1] / 1024 if mb_range[1] is not None else None
        return (min_gb, max_gb)

    @classmethod
    def from_mb(cls, mb: float) -> EnumMemoryUsage:
        """Determine category from memory usage in MB."""
        # Memory threshold classification - architectural design for memory categories
        if mb < 10:
            return cls.MINIMAL
        if mb < 50:
            return cls.TINY
        if mb < 100:
            return cls.SMALL
        if mb < 250:
            return cls.LOW
        if mb < 500:
            return cls.MODERATE
        if mb < 1024:
            return cls.MEDIUM
        if mb < 2048:
            return cls.HIGH
        if mb < 4096:
            return cls.LARGE
        if mb < 8192:
            return cls.VERY_HIGH
        if mb < 16384:
            return cls.EXTREME
        return cls.MASSIVE

    @classmethod
    def from_gb(cls, gb: float) -> EnumMemoryUsage:
        """Determine category from memory usage in GB."""
        return cls.from_mb(gb * 1024)

    @classmethod
    def get_low_memory_categories(cls) -> list[EnumMemoryUsage]:
        """Get categories for low memory operations."""
        return [
            cls.MINIMAL,
            cls.TINY,
            cls.SMALL,
            cls.LOW,
        ]

    @classmethod
    def get_high_memory_categories(cls) -> list[EnumMemoryUsage]:
        """Get categories for high memory operations."""
        return [
            cls.VERY_HIGH,
            cls.EXTREME,
            cls.MASSIVE,
        ]

    @property
    def is_low_memory(self) -> bool:
        """Check if this is a low memory category."""
        return self in self.get_low_memory_categories()

    @property
    def is_high_memory(self) -> bool:
        """Check if this is a high memory category."""
        return self in self.get_high_memory_categories()


# Export for use
__all__ = ["EnumMemoryUsage"]
