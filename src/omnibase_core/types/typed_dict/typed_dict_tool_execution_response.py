"""TypedDict for tool execution response data."""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolExecutionResponse(TypedDict):
    """TypedDict for tool execution response data."""

    tool_name: str
    success: bool
    result: object | None
    execution_time: float
    error: str | None
    tool_version: str


__all__ = ["TypedDictToolExecutionResponse"]
