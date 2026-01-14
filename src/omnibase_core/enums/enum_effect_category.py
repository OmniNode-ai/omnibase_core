"""Effect Category Enum for non-deterministic effect classification.

Categorizes external effects by their nature for replay safety analysis.
Part of the effect boundary system for OMN-1147.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumEffectCategory"]


@unique
class EnumEffectCategory(StrValueHelper, str, Enum):
    """Categories of non-deterministic effects for replay safety classification.

    Each category represents a class of external interactions that may produce
    different results on replay. Used by the effect boundary system to enforce
    determinism policies during execution.
    """

    NETWORK = "network"
    """HTTP calls, socket operations, DNS lookups."""

    TIME = "time"
    """Current time, timestamps, durations based on wall clock."""

    RANDOM = "random"
    """Random number generation, UUID generation."""

    EXTERNAL_STATE = "external_state"
    """Environment variables, config files, system properties."""

    FILESYSTEM = "filesystem"
    """File reads/writes, directory operations."""

    DATABASE = "database"
    """Queries, transactions, connection state."""

    @classmethod
    def is_io_category(cls, category: "EnumEffectCategory") -> bool:
        """Check if category involves external I/O operations."""
        return category in {cls.NETWORK, cls.FILESYSTEM, cls.DATABASE}

    @classmethod
    def is_temporal_category(cls, category: "EnumEffectCategory") -> bool:
        """Check if category depends on time or randomness."""
        return category in {cls.TIME, cls.RANDOM}

    @classmethod
    def requires_isolation(cls, category: "EnumEffectCategory") -> bool:
        """Check if category requires isolation mechanisms for safe replay.

        Categories that require isolation benefit from mechanisms like
        database snapshots, filesystem sandboxing, or environment isolation
        to ensure deterministic replay behavior.

        Args:
            category: The effect category to check.

        Returns:
            True if the category benefits from isolation mechanisms.
        """
        return category in {cls.DATABASE, cls.FILESYSTEM, cls.EXTERNAL_STATE}
