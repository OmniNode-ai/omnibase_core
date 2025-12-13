"""TypedDict for health check status from MixinHealthCheck."""

from __future__ import annotations

from typing import TypedDict


class TypedDictHealthCheckStatus(TypedDict):
    """TypedDict for health check status from MixinHealthCheck."""

    node_id: str
    is_healthy: bool
    status: str
    health_score: float
    issues: list[str]


__all__ = ["TypedDictHealthCheckStatus"]
