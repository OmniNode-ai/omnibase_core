"""TypedDict for node executor health status from MixinNodeExecutor.get_executor_health()."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictNodeExecutorHealth(TypedDict):
    """TypedDict for node executor health status from MixinNodeExecutor.get_executor_health()."""

    status: str
    uptime_seconds: int
    active_invocations: int
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    success_rate: float
    node_id: str | UUID
    node_name: str
    shutdown_requested: bool


__all__ = ["TypedDictNodeExecutorHealth"]
