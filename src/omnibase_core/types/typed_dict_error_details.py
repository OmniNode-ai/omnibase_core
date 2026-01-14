"""
TypedDict for error details.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict


class TypedDictErrorDetails(TypedDict):
    error_code: str
    error_message: str
    error_type: str
    timestamp: datetime
    stack_trace: NotRequired[str]
    context: NotRequired[dict[str, str]]


__all__ = ["TypedDictErrorDetails"]
