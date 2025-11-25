"""
Protocol Cache Singleton Holder.

Thread-safe singleton holder for protocol cache instances,
managing cached protocol services for logging infrastructure
with TTL-based expiration.

Thread Safety:
    All methods use internal locking for thread-safe access.
"""

import threading
import time


class _ProtocolCacheHolder:
    """
    Thread-safe protocol cache singleton holder.

    Manages cached protocol services for logging infrastructure
    with TTL-based expiration.

    Thread Safety:
        All public methods are thread-safe using internal locking.
    """

    _formatter: object | None = None
    _output_handler: object | None = None
    _timestamp: float = 0.0
    _ttl: float = 300.0  # 5 minutes TTL
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_formatter(cls) -> object | None:
        """Get cached formatter (thread-safe)."""
        with cls._lock:
            if cls._is_expired():
                cls._formatter = None
            return cls._formatter

    @classmethod
    def set_formatter(cls, formatter: object | None) -> None:
        """Set cached formatter (thread-safe)."""
        with cls._lock:
            cls._formatter = formatter

    @classmethod
    def get_output_handler(cls) -> object | None:
        """Get cached output handler (thread-safe)."""
        with cls._lock:
            if cls._is_expired():
                cls._output_handler = None
            return cls._output_handler

    @classmethod
    def set_output_handler(cls, handler: object | None) -> None:
        """Set cached output handler (thread-safe)."""
        with cls._lock:
            cls._output_handler = handler

    @classmethod
    def get_timestamp(cls) -> float:
        """Get cache timestamp (thread-safe)."""
        with cls._lock:
            return cls._timestamp

    @classmethod
    def set_timestamp(cls, timestamp: float) -> None:
        """Set cache timestamp (thread-safe)."""
        with cls._lock:
            cls._timestamp = timestamp

    @classmethod
    def get_ttl(cls) -> float:
        """Get cache TTL."""
        return cls._ttl

    @classmethod
    def _is_expired(cls) -> bool:
        """Check if cache is expired (internal, assumes lock held)."""
        return (time.time() - cls._timestamp) > cls._ttl
