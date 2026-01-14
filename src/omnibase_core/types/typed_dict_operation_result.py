"""
TypedDict for operation results.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict

from .typed_dict_error_details import TypedDictErrorDetails


class TypedDictOperationResult(TypedDict):
    success: bool
    result_type: str
    execution_time_ms: int
    timestamp: datetime
    error_details: NotRequired[TypedDictErrorDetails]


__all__ = ["TypedDictOperationResult"]
