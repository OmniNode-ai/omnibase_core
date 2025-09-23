"""
Namespace strategy enumeration.

Defines strategies for namespace handling in ONEX configuration system.
"""

from __future__ import annotations

from enum import Enum


class EnumNamespaceStrategy(str, Enum):
    """
    Enumeration of namespace handling strategies.

    Used for configuring how namespaces are resolved and managed.
    """

    # Standard strategies
    ONEX_DEFAULT = "onex_default"
    EXPLICIT = "explicit"
    AUTO = "auto"

    def __str__(self) -> str:
        """Return the string value for serialization."""
        return self.value

    @classmethod
    def is_automatic(cls, strategy: EnumNamespaceStrategy) -> bool:
        """Check if strategy uses automatic namespace resolution."""
        return strategy in {cls.ONEX_DEFAULT, cls.AUTO}

    @classmethod
    def requires_explicit_definition(cls, strategy: EnumNamespaceStrategy) -> bool:
        """Check if strategy requires explicit namespace definitions."""
        return strategy == cls.EXPLICIT

    @classmethod
    def get_default_strategy(cls) -> EnumNamespaceStrategy:
        """Get the default namespace strategy."""
        return cls.ONEX_DEFAULT


# Export the enum
__all__ = ["EnumNamespaceStrategy"]
