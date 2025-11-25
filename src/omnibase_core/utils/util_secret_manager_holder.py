"""
Secret Manager Singleton Holder.

Thread-safe singleton holder for secret manager instances,
supporting the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.

Thread Safety:
    All get/set operations are protected by a threading.Lock to ensure
    thread-safe access to the singleton instance across concurrent threads.
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.security.model_secret_manager import ModelSecretManager


class _SecretManagerHolder:
    """
    Thread-safe secret manager singleton holder.

    Uses a class-level lock to protect concurrent access to the singleton
    instance. All get/set operations acquire the lock before accessing
    the shared state.

    Thread Safety:
        - get(): Acquires lock before reading _instance
        - set(): Acquires lock before writing _instance
    """

    _instance: ModelSecretManager | None = None
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get(cls) -> ModelSecretManager | None:
        """
        Get the secret manager instance.

        Returns:
            The secret manager instance, or None if not set.

        Thread Safety:
            This method acquires the class lock before reading.
        """
        with cls._lock:
            return cls._instance

    @classmethod
    def set(cls, manager: ModelSecretManager) -> None:
        """
        Set the secret manager instance.

        Args:
            manager: The secret manager instance to store.

        Thread Safety:
            This method acquires the class lock before writing.
        """
        with cls._lock:
            cls._instance = manager
