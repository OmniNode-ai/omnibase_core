from __future__ import annotations

"""
Fallback protocol log context for ONEX structured logging.

Provides fallback implementation when omnibase_spi is not available.
Follows ONEX strong typing principles and one-model-per-file architecture.
"""


from typing import Any, Protocol


class ProtocolLogContextFallback(Protocol):
    """Fallback protocol for log context when omnibase_spi is not available."""

    def to_dict(self) -> dict[str, Any]: ...


# Export for use
__all__ = ["ProtocolLogContextFallback"]
