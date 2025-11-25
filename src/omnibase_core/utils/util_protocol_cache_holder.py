"""
Protocol Cache Singleton Holder.

Thread-safe singleton holder for protocol cache instances,
managing cached protocol services for logging infrastructure
with TTL-based expiration.
"""

import threading
from typing import Any


class _ProtocolCacheHolder:
    """
    Thread-safe protocol cache singleton holder.

    Manages cached protocol services for logging infrastructure
    with TTL-based expiration.
    """

    _formatter: Any | None = None
    _output_handler: Any | None = None
    _timestamp: float = 0.0
    _ttl: float = 300  # 5 minutes TTL
    _lock = threading.Lock()

    @classmethod
    def get_formatter(cls) -> Any | None:
        """Get cached formatter."""
        return cls._formatter

    @classmethod
    def set_formatter(cls, formatter: Any) -> None:
        """Set cached formatter."""
        cls._formatter = formatter

    @classmethod
    def get_output_handler(cls) -> Any | None:
        """Get cached output handler."""
        return cls._output_handler

    @classmethod
    def set_output_handler(cls, handler: Any) -> None:
        """Set cached output handler."""
        cls._output_handler = handler

    @classmethod
    def get_timestamp(cls) -> float:
        """Get cache timestamp."""
        return cls._timestamp

    @classmethod
    def set_timestamp(cls, timestamp: float) -> None:
        """Set cache timestamp."""
        cls._timestamp = timestamp

    @classmethod
    def get_ttl(cls) -> float:
        """Get cache TTL."""
        return cls._ttl
