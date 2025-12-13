"""TypedDict for service health status from MixinNodeService."""

from __future__ import annotations

from typing import TypedDict
from uuid import UUID


class TypedDictServiceHealth(TypedDict):
    """TypedDict for service health status from MixinNodeService."""

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


__all__ = ["TypedDictServiceHealth"]
