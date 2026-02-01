"""
TypedDict for structured log context.

Used by MessageDispatchEngine for structured logging with the `extra` parameter.
All fields are optional since context is built incrementally.
"""

from __future__ import annotations

from typing import TypedDict

__all__ = ["TypedDictLogContext"]


class TypedDictLogContext(TypedDict, total=False):
    """
    TypedDict for structured log context.

    Used in logging `extra` parameter for structured observability.
    All fields are optional (total=False) since context is built incrementally
    based on what information is available at each log point.
    """

    topic: str
    category: str
    message_type: str
    handler_id: str
    handler_count: int
    duration_ms: float
    correlation_id: str
    trace_id: str
    dispatch_id: str  # string-id-ok: UUID serialized as string for JSON logging
    error_code: str
