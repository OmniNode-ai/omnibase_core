from __future__ import annotations

from datetime import datetime

"""
Legacy error input structure for converter functions.
"""

from typing import TypedDict


class TypedDictLegacyError(TypedDict, total=False):
    """Legacy error input structure for converter functions."""

    error_code: str | None
    error_message: str | None
    error_type: str | None
    timestamp: str | None  # String representation of datetime
    stack_trace: str | None
    context: dict[str, str | None] | None
