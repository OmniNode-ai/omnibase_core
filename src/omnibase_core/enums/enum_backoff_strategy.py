"""
Backoff Strategy Enum

Retry backoff strategies for webhook notification delivery.
"""

from enum import Enum


class EnumBackoffStrategy(str, Enum):
    """
    Retry backoff strategies for webhook notification delivery.

    Defines how the delay between retry attempts should be calculated
    in the ONEX infrastructure notification system.
    """

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"

    def __str__(self) -> str:
        """Return the string value of the backoff strategy."""
        return self.value

    def is_exponential(self) -> bool:
        """Check if this is exponential backoff."""
        return self == self.EXPONENTIAL

    def is_linear(self) -> bool:
        """Check if this is linear backoff."""
        return self == self.LINEAR

    def is_fixed(self) -> bool:
        """Check if this is fixed delay backoff."""
        return self == self.FIXED

    def calculate_delay(self, base_delay: float, attempt_number: int) -> float:
        """
        Calculate the delay for a given attempt.

        Args:
            base_delay: Base delay in seconds
            attempt_number: The attempt number (1-based)

        Returns:
            float: Delay in seconds
        """
        if attempt_number <= 1:
            return base_delay

        if self == self.EXPONENTIAL:
            return base_delay * (2 ** (attempt_number - 1))
        elif self == self.LINEAR:
            return base_delay * attempt_number
        else:  # FIXED
            return base_delay
