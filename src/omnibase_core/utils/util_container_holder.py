"""
Container Singleton Holder.

Thread-safe singleton holder for container instances,
supporting the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.
"""

from typing import Any


class _ContainerHolder:
    """Thread-safe container singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get container instance."""
        return cls._instance

    @classmethod
    def set(cls, container: Any) -> None:
        """Set container instance."""
        cls._instance = container
