"""TypedDict for node executor health status from MixinNodeExecutor.get_executor_health()."""

from __future__ import annotations

from typing import TypedDict


class TypedDictNodeExecutorHealth(TypedDict):
    """TypedDict for node executor health status from MixinNodeExecutor.get_executor_health().

    Note: node_id is always str - UUIDs should be converted to string at boundaries
    for type safety and JSON serialization compatibility.
    """

    status: str
    uptime_seconds: int
    active_invocations: int
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    success_rate: float
    node_id: str  # Always str - UUIDs converted at boundaries for type safety
    node_name: str
    shutdown_requested: bool


__all__ = ["TypedDictNodeExecutorHealth"]
