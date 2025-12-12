"""TypedDict for tool execution response data."""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolExecutionResponse(TypedDict):
    """TypedDict for tool execution response data.

    Note: execution_time_ms is int for consistency with TypedDictToolExecutionResult
    and standard millisecond precision (no fractional milliseconds needed).
    """

    tool_name: str
    success: bool
    result: object | None
    execution_time_ms: int  # int for consistency with TypedDictToolExecutionResult
    error: str | None
    tool_version: str


__all__ = ["TypedDictToolExecutionResponse"]
