"""
Command Registry Singleton Holder.

Thread-safe singleton holder for command registry instances,
supporting the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.
"""

from typing import Any


class _CommandRegistryHolder:
    """Thread-safe command registry singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get registry instance."""
        return cls._instance

    @classmethod
    def set(cls, registry: Any) -> None:
        """Set registry instance."""
        cls._instance = registry
