"""
TypedDict for configuration settings.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictConfigurationSettings(TypedDict):
    environment: str
    debug_enabled: bool
    log_level: str
    timeout_ms: int
    retry_attempts: int
    batch_size: int


__all__ = ["TypedDictConfigurationSettings"]
