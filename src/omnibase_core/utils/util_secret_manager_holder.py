"""
Secret Manager Singleton Holder.

Thread-safe singleton holder for secret manager instances,
supporting the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.
"""

from typing import Any


class _SecretManagerHolder:
    """Thread-safe secret manager singleton holder."""

    _instance: Any = None

    @classmethod
    def get(cls) -> Any:
        """Get secret manager instance."""
        return cls._instance

    @classmethod
    def set(cls, manager: Any) -> None:
        """Set secret manager instance."""
        cls._instance = manager
