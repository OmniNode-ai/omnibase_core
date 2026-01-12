"""
Likelihood Enumeration.

Likelihood levels for risk assessment and probability estimation in ONEX infrastructure.
Used by context models to express probability or confidence levels.
"""

from __future__ import annotations

from enum import Enum, unique
from functools import cache

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumLikelihood"]


@unique
class EnumLikelihood(StrValueHelper, str, Enum):
    """
    Enumeration for likelihood or probability levels.

    This enum represents discrete probability ranges for risk assessment and
    confidence estimation. Each level maps to a specific probability range
    using standard mathematical interval notation:

    Interval Notation:
        - [a, b) means a <= x < b (inclusive lower, exclusive upper)
        - (a, b) means a < x < b (exclusive both ends)
        - {x} means exactly x (singleton set)

    Boundary Behavior:
        At exact boundary values, the probability maps to the HIGHER category.
        For example, 0.1 exactly returns LOW (not VERY_LOW), and 0.3 exactly
        returns MEDIUM (not LOW). This follows the [lower, upper) convention
        where the lower bound is inclusive for most categories.

        Special cases:
            - VERY_LOW uses (0.0, 0.1) notation: 0.0 is EXCLUDED (returns IMPOSSIBLE)
            - IMPOSSIBLE and CERTAIN are singletons: exactly 0.0 and 1.0 respectively

    Probability Mapping (used by from_probability):
        IMPOSSIBLE: {0.0}           - Exactly 0% probability
        VERY_LOW:   (0.0, 0.1)      - Greater than 0%, less than 10%
        LOW:        [0.1, 0.3)      - 10% (inclusive) to less than 30%
        MEDIUM:     [0.3, 0.6)      - 30% (inclusive) to less than 60%
        HIGH:       [0.6, 0.85)     - 60% (inclusive) to less than 85%
        VERY_HIGH:  [0.85, 1.0)     - 85% (inclusive) to less than 100%
        CERTAIN:    {1.0}           - Exactly 100% probability
        UNKNOWN:    [0.0, 1.0]      - Probability cannot be determined

    Examples:
        >>> EnumLikelihood.from_probability(0.0)
        <EnumLikelihood.IMPOSSIBLE: 'impossible'>
        >>> EnumLikelihood.from_probability(0.1)  # Boundary: returns LOW
        <EnumLikelihood.LOW: 'low'>
        >>> EnumLikelihood.from_probability(0.09999)  # Just below: returns VERY_LOW
        <EnumLikelihood.VERY_LOW: 'very_low'>
    """

    # Ordered from lowest to highest probability
    # Notation: [a, b) = inclusive lower, exclusive upper; (a, b) = exclusive both ends
    VERY_LOW = "very_low"  # (0.0, 0.1) - Very unlikely, but not impossible (0 excluded)
    LOW = "low"  # [0.1, 0.3) - Unlikely to occur
    MEDIUM = "medium"  # [0.3, 0.6) - Moderately likely
    HIGH = "high"  # [0.6, 0.85) - Likely to occur
    VERY_HIGH = "very_high"  # [0.85, 1.0) - Very likely, but not certain

    # Special values (exact probabilities)
    UNKNOWN = "unknown"  # Probability cannot be determined
    CERTAIN = "certain"  # {1.0} - Will definitely occur (exactly 100%)
    IMPOSSIBLE = "impossible"  # {0.0} - Will never occur (exactly 0%)

    @classmethod
    @cache
    def _get_probability_ranges(cls) -> dict[EnumLikelihood, tuple[float, float]]:
        """Return cached probability ranges dictionary.

        Uses functools.cache for memoization to avoid recreating the dict on each call.
        """
        return {
            cls.IMPOSSIBLE: (0.0, 0.0),
            cls.VERY_LOW: (0.0, 0.1),
            cls.LOW: (0.1, 0.3),
            cls.MEDIUM: (0.3, 0.6),
            cls.HIGH: (0.6, 0.85),
            cls.VERY_HIGH: (0.85, 1.0),
            cls.CERTAIN: (1.0, 1.0),
            cls.UNKNOWN: (0.0, 1.0),
        }

    @classmethod
    def get_numeric_range(cls, likelihood: EnumLikelihood) -> tuple[float, float]:
        """
        Get the numeric probability range for a likelihood level.

        Returns a tuple (min, max) representing the probability range for the
        given likelihood level. The tuple values represent the boundaries;
        see the class docstring for precise boundary semantics.

        Range Definitions (returned as tuple values):
            IMPOSSIBLE: (0.0, 0.0)  - Singleton {0.0}: exactly 0%
            VERY_LOW:   (0.0, 0.1)  - Range (0.0, 0.1): 0% < p < 10%
            LOW:        (0.1, 0.3)  - Range [0.1, 0.3): 10% <= p < 30%
            MEDIUM:     (0.3, 0.6)  - Range [0.3, 0.6): 30% <= p < 60%
            HIGH:       (0.6, 0.85) - Range [0.6, 0.85): 60% <= p < 85%
            VERY_HIGH:  (0.85, 1.0) - Range [0.85, 1.0): 85% <= p < 100%
            CERTAIN:    (1.0, 1.0)  - Singleton {1.0}: exactly 100%
            UNKNOWN:    (0.0, 1.0)  - Full range [0.0, 1.0]: indeterminate

        Note:
            The returned tuple (min, max) represents boundary values only, NOT the
            actual interval semantics. For example, both VERY_LOW and LOW return
            tuples containing 0.1, but VERY_LOW excludes it (upper bound) while
            LOW includes it (lower bound). The actual inclusive/exclusive semantics
            are defined by from_probability(). Use from_probability() for precise
            probability-to-likelihood mapping.

        Args:
            likelihood: The likelihood level to convert

        Returns:
            A tuple of (min_probability, max_probability) as floats in [0.0, 1.0]
        """
        return cls._get_probability_ranges().get(likelihood, (0.0, 1.0))

    @classmethod
    def from_probability(cls, probability: float) -> EnumLikelihood:
        """
        Convert a numeric probability to a likelihood level.

        Args:
            probability: A float between 0.0 and 1.0 (inclusive)

        Returns:
            The corresponding likelihood level

        Raises:
            ModelOnexError: If probability is outside the valid range [0.0, 1.0]

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
            # Lazy import to avoid circular dependency and maintain import chain
            from omnibase_core.errors import ModelOnexError

            raise ModelOnexError(
                message=f"probability must be between 0.0 and 1.0, got {probability}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                probability=probability,
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
