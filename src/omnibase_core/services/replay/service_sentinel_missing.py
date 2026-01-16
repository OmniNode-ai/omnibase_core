"""
Sentinel value for missing configuration paths.

This module provides a singleton sentinel to distinguish "path not found"
from "value is None" during config override traversal.

.. versionadded:: 0.4.0
    Added Configuration Override Injection (OMN-1205)
"""


class _Missing:
    """Singleton sentinel class for missing values (distinct from None).

    Used during path traversal to distinguish between:
    - Path exists but value is None
    - Path does not exist (returns MISSING)

    Thread Safety:
        Singleton pattern is thread-safe for reads. The instance is created
        at module load time.
    """

    _instance: "_Missing | None" = None

    def __new__(cls) -> "_Missing":
        """Return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        """Return string representation."""
        return "<MISSING>"

    def __bool__(self) -> bool:
        """Always return False for truthiness checks."""
        return False


# Module-level singleton instance
MISSING = _Missing()

__all__ = ["MISSING"]
