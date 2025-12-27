from __future__ import annotations

"""
Likelihood Enumeration.

Likelihood levels for risk assessment and probability estimation in ONEX infrastructure.
Used by context models to express probability or confidence levels.
"""

from enum import Enum


class EnumLikelihood(str, Enum):
    """Enumeration for likelihood or probability levels."""

    # Ordered from lowest to highest
    # Boundary note: Each level's lower bound is inclusive, upper bound is exclusive
    # Example: 0.1 returns LOW (not VERY_LOW), 0.3 returns MEDIUM (not LOW)
    VERY_LOW = "very_low"  # Very unlikely to occur (0% < p < 10%)
    LOW = "low"  # Unlikely to occur (10% <= p < 30%)
    MEDIUM = "medium"  # Moderately likely to occur (30% <= p < 60%)
    HIGH = "high"  # Likely to occur (60% <= p < 85%)
    VERY_HIGH = "very_high"  # Very likely to occur (85% <= p < 100%)

    # Special values
    UNKNOWN = "unknown"  # Likelihood cannot be determined
    CERTAIN = "certain"  # Will definitely occur (100%)
    IMPOSSIBLE = "impossible"  # Will never occur (0%)

    def __str__(self) -> str:
        """Return the string value of the likelihood level."""
        return self.value

    @classmethod
    def get_numeric_range(cls, likelihood: EnumLikelihood) -> tuple[float, float]:
        """
        Get the approximate numeric probability range for a likelihood level.

        Args:
            likelihood: The likelihood level to convert

        Returns:
            A tuple of (min_probability, max_probability) as floats 0.0-1.0
        """
        ranges: dict[EnumLikelihood, tuple[float, float]] = {
            cls.IMPOSSIBLE: (0.0, 0.0),
            cls.VERY_LOW: (0.0, 0.1),
            cls.LOW: (0.1, 0.3),
            cls.MEDIUM: (0.3, 0.6),
            cls.HIGH: (0.6, 0.85),
            cls.VERY_HIGH: (0.85, 1.0),
            cls.CERTAIN: (1.0, 1.0),
            cls.UNKNOWN: (0.0, 1.0),  # Full range when unknown
        }
        return ranges.get(likelihood, (0.0, 1.0))

    @classmethod
    def from_probability(cls, probability: float) -> EnumLikelihood:
        """
        Convert a numeric probability to a likelihood level.

        Args:
            probability: A float between 0.0 and 1.0

        Returns:
            The corresponding likelihood level
        """
        if probability <= 0.0:
            return cls.IMPOSSIBLE
        elif probability < 0.1:
            return cls.VERY_LOW
        elif probability < 0.3:
            return cls.LOW
        elif probability < 0.6:
            return cls.MEDIUM
        elif probability < 0.85:
            return cls.HIGH
        elif probability < 1.0:
            return cls.VERY_HIGH
        else:
            return cls.CERTAIN

    @classmethod
    def is_determinable(cls, likelihood: EnumLikelihood) -> bool:
        """
        Check if the likelihood represents a determinable probability.

        Args:
            likelihood: The likelihood level to check

        Returns:
            True if the likelihood is known, False if unknown
        """
        return likelihood != cls.UNKNOWN
