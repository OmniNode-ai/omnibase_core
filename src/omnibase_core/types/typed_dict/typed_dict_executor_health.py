"""TypedDict for executor health status from MixinNodeExecutor."""

from __future__ import annotations

from typing import TypedDict


class TypedDictExecutorHealth(TypedDict):
    """TypedDict for executor health status from MixinNodeExecutor."""

    status: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    circuit_breaker_state: str
    last_execution_time: str | None


__all__ = ["TypedDictExecutorHealth"]
