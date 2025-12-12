"""TypedDict for tool execution result."""

from __future__ import annotations

from typing import TypedDict


class TypedDictToolExecutionResult(TypedDict):
    """TypedDict for tool execution result."""

    success: bool
    result: object | None
    error: str | None
    execution_time_ms: int


__all__ = ["TypedDictToolExecutionResult"]
