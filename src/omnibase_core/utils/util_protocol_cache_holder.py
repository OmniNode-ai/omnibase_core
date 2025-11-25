"""
Protocol Cache Singleton Holder.

Thread-safe singleton holder for protocol cache instances,
managing cached protocol services for logging infrastructure
with TTL-based expiration.

Thread Safety:
    All methods use internal locking for thread-safe access.

BOUNDARY_LAYER_EXCEPTION:
    Uses Any for formatter/output_handler types because the actual protocol
    types (ProtocolSmartLogFormatter, ProtocolContextAwareOutputHandler) are
    planned infrastructure not yet implemented. The logging system gracefully
    handles their absence with fallback behavior.
"""

import threading
import time
from typing import Any


class _ProtocolCacheHolder:
    """
    Thread-safe protocol cache singleton holder.

    Manages cached protocol services for logging infrastructure
    with TTL-based expiration.

    Thread Safety:
        All public methods are thread-safe using internal locking.

    BOUNDARY_LAYER_EXCEPTION:
        Uses Any for cached services because protocol types are not yet defined.
    """

    # BOUNDARY_LAYER_EXCEPTION: Any required - protocol types not yet implemented
    _formatter: Any = None
    _output_handler: Any = None
    _timestamp: float = 0.0
    _ttl: float = 300.0  # 5 minutes TTL
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_formatter(cls) -> Any:
        """Get cached formatter (thread-safe)."""
        with cls._lock:
            if cls._is_expired():
                cls._formatter = None
            return cls._formatter

    @classmethod
    def set_formatter(cls, formatter: Any) -> None:
        """Set cached formatter (thread-safe)."""
        with cls._lock:
            cls._formatter = formatter
            cls._timestamp = time.time()

    @classmethod
    def get_output_handler(cls) -> Any:
        """Get cached output handler (thread-safe)."""
        with cls._lock:
            if cls._is_expired():
                cls._output_handler = None
            return cls._output_handler

    @classmethod
    def set_output_handler(cls, handler: Any) -> None:
        """Set cached output handler (thread-safe)."""
        with cls._lock:
            cls._output_handler = handler
            cls._timestamp = time.time()

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
        """Get cache TTL (thread-safe)."""
        with cls._lock:
            return cls._ttl

    @classmethod
    def _is_expired(cls) -> bool:
        """Check if cache is expired (internal, assumes lock held)."""
        return (time.time() - cls._timestamp) > cls._ttl
