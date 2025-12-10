from __future__ import annotations

"""
TypedDict for operation results.
"""


from datetime import datetime
from typing import NotRequired, TypedDict

from .typed_dict_error_details import TypedDictErrorDetails


class TypedDictOperationResult(TypedDict):
    """TypedDict for operation results."""

    success: bool
    result_type: str
    execution_time_ms: int
    timestamp: datetime
    error_details: NotRequired[TypedDictErrorDetails]


__all__ = ["TypedDictOperationResult"]
