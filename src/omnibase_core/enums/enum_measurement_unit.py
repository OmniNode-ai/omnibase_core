"""
Measurement unit enumeration for data quantification.

Provides strongly typed measurement unit values for data analysis and metrics.
Follows ONEX one-enum-per-file naming conventions.
"""

from enum import Enum


class EnumMeasurementUnit(str, Enum):
    """
    Strongly typed measurement unit for data quantification.

    Inherits from str for JSON serialization compatibility while providing
    type safety and IDE support.
    """

    # Dimensionless
    COUNT = "count"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    SCORE = "score"

    # Time
    SECONDS = "seconds"
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"

    # Data size
    BYTES = "bytes"
    KILOBYTES = "kilobytes"
    MEGABYTES = "megabytes"
    GIGABYTES = "gigabytes"

    # Performance
    REQUESTS_PER_SECOND = "requests_per_second"
    OPERATIONS_PER_SECOND = "operations_per_second"
    TRANSACTIONS_PER_MINUTE = "transactions_per_minute"

    # Currency
    USD = "usd"
    EUR = "eur"

    # Business metrics
    USERS = "users"
    SESSIONS = "sessions"
    CONVERSIONS = "conversions"

    # Technical metrics
    CPU_PERCENT = "cpu_percent"
    MEMORY_PERCENT = "memory_percent"
    LATENCY_MS = "latency_ms"

    # Custom
    CUSTOM = "custom"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_time_based(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit is time-based."""
        return unit in {cls.SECONDS, cls.MINUTES, cls.HOURS, cls.DAYS, cls.LATENCY_MS}

    @classmethod
    def is_data_size(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit is data size."""
        return unit in {cls.BYTES, cls.KILOBYTES, cls.MEGABYTES, cls.GIGABYTES}

    @classmethod
    def is_rate_based(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit is rate-based."""
        return unit in {cls.REQUESTS_PER_SECOND, cls.OPERATIONS_PER_SECOND, cls.TRANSACTIONS_PER_MINUTE}

    @classmethod
    def is_percentage(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit is percentage-based."""
        return unit in {cls.PERCENTAGE, cls.CPU_PERCENT, cls.MEMORY_PERCENT}

    @classmethod
    def is_currency(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit is currency."""
        return unit in {cls.USD, cls.EUR}

    @classmethod
    def requires_aggregation(cls, unit: "EnumMeasurementUnit") -> bool:
        """Check if the measurement unit typically requires aggregation."""
        return unit in {cls.COUNT, cls.USERS, cls.SESSIONS, cls.CONVERSIONS, cls.REQUESTS_PER_SECOND}


# Export for use
__all__ = ["EnumMeasurementUnit"]