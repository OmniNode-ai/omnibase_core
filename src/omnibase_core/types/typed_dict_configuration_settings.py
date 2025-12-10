from __future__ import annotations

"""
TypedDict for configuration settings.
"""

from typing import TypedDict


class TypedDictConfigurationSettings(TypedDict):
    """TypedDict for configuration settings."""

    environment: str
    debug_enabled: bool
    log_level: str
    timeout_ms: int
    retry_attempts: int
    batch_size: int


__all__ = ["TypedDictConfigurationSettings"]
