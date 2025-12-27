"""
Likelihood Enumeration.

Likelihood levels for risk assessment and probability estimation in ONEX infrastructure.
Used by context models to express probability or confidence levels.
"""

from __future__ import annotations

from enum import Enum


class EnumLikelihood(str, Enum):
    """
    Enumeration for likelihood or probability levels.

    This enum represents discrete probability ranges for risk assessment and
    confidence estimation. Each level maps to a specific probability range
    using standard mathematical interval notation:
    - [a, b) means a <= x < b (inclusive lower, exclusive upper)
    - {x} means exactly x (singleton)

    Probability Mapping (used by from_probability):
        IMPOSSIBLE: {0.0}           - Exactly 0% probability
        VERY_LOW:   (0.0, 0.1)      - Greater than 0% and less than 10%
        LOW:        [0.1, 0.3)      - 10% to less than 30%
        MEDIUM:     [0.3, 0.6)      - 30% to less than 60%
        HIGH:       [0.6, 0.85)     - 60% to less than 85%
        VERY_HIGH:  [0.85, 1.0)     - 85% to less than 100%
        CERTAIN:    {1.0}           - Exactly 100% probability
        UNKNOWN:    Full range      - Probability cannot be determined

    Examples:
        >>> EnumLikelihood.from_probability(0.0)
        <EnumLikelihood.IMPOSSIBLE: 'impossible'>
        >>> EnumLikelihood.from_probability(0.1)  # Boundary: returns LOW
        <EnumLikelihood.LOW: 'low'>
        >>> EnumLikelihood.from_probability(0.09999)  # Just below: returns VERY_LOW
        <EnumLikelihood.VERY_LOW: 'very_low'>
    """

    # Ordered from lowest to highest probability
    # Notation: [lower, upper) means lower <= p < upper
    VERY_LOW = "very_low"  # (0.0, 0.1) - Very unlikely, but not impossible
    LOW = "low"  # [0.1, 0.3) - Unlikely to occur
    MEDIUM = "medium"  # [0.3, 0.6) - Moderately likely
    HIGH = "high"  # [0.6, 0.85) - Likely to occur
    VERY_HIGH = "very_high"  # [0.85, 1.0) - Very likely, but not certain

    # Special values (exact probabilities)
    UNKNOWN = "unknown"  # Probability cannot be determined
    CERTAIN = "certain"  # {1.0} - Will definitely occur (exactly 100%)
    IMPOSSIBLE = "impossible"  # {0.0} - Will never occur (exactly 0%)

    def __str__(self) -> str:
        """Return the string value of the likelihood level."""
        return self.value

    @classmethod
    def get_numeric_range(cls, likelihood: EnumLikelihood) -> tuple[float, float]:
        """
        Get the numeric probability range for a likelihood level.

        Returns a tuple (min, max) representing the probability range for the
        given likelihood level. For standard levels, ranges use [min, max)
        notation (inclusive min, exclusive max).

        Range Definitions:
            IMPOSSIBLE: (0.0, 0.0)  - Singleton: exactly 0%
            VERY_LOW:   (0.0, 0.1)  - Exclusive both ends: 0% < p < 10%
            LOW:        (0.1, 0.3)  - 10% <= p < 30%
            MEDIUM:     (0.3, 0.6)  - 30% <= p < 60%
            HIGH:       (0.6, 0.85) - 60% <= p < 85%
            VERY_HIGH:  (0.85, 1.0) - 85% <= p < 100%
            CERTAIN:    (1.0, 1.0)  - Singleton: exactly 100%
            UNKNOWN:    (0.0, 1.0)  - Full range (probability indeterminate)

        Note:
            The returned ranges are approximate representations. Use
            from_probability() for precise probability-to-likelihood mapping.

        Args:
            likelihood: The likelihood level to convert

        Returns:
            A tuple of (min_probability, max_probability) as floats in [0.0, 1.0]
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
            probability: A float between 0.0 and 1.0 (inclusive)

        Returns:
            The corresponding likelihood level

        Raises:
            ValueError: If probability is outside the valid range [0.0, 1.0]

        Boundary Behavior:
            - 0.0: Returns IMPOSSIBLE
            - (0.0, 0.1): Returns VERY_LOW
            - [0.1, 0.3): Returns LOW
            - [0.3, 0.6): Returns MEDIUM
            - [0.6, 0.85): Returns HIGH
            - [0.85, 1.0): Returns VERY_HIGH
            - 1.0: Returns CERTAIN

        Examples:
            >>> EnumLikelihood.from_probability(0.5)
            <EnumLikelihood.MEDIUM: 'medium'>
            >>> EnumLikelihood.from_probability(0.0)
            <EnumLikelihood.IMPOSSIBLE: 'impossible'>
            >>> EnumLikelihood.from_probability(1.0)
            <EnumLikelihood.CERTAIN: 'certain'>
        """
        if not 0.0 <= probability <= 1.0:
            raise ValueError(
                f"probability must be between 0.0 and 1.0, got {probability}"
            )
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
