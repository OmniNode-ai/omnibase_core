"""
Logger Cache Singleton Holder.

Thread-safe singleton holder for logger cache instances,
supporting the DI container pattern with fallback mechanisms
for bootstrap and circular dependency scenarios.
"""

import threading
from typing import Any


class _LoggerCache:
    """Thread-safe logger cache holder."""

    _instance: Any = None
    _lock = threading.Lock()

    @classmethod
    def get(cls) -> Any | None:
        """Get cached logger instance.

        Thread-safe access to the cached logger.
        """
        with cls._lock:
            return cls._instance

    @classmethod
    def set(cls, logger: Any) -> None:
        """Set cached logger instance.

        Thread-safe modification of the cached logger.
        """
        with cls._lock:
            cls._instance = logger
