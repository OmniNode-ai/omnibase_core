"""TypedDict for health status dictionary returned by get_health_status().

Provides better type information for consumers than a generic dict type,
enabling IDE autocomplete and stricter type checking.
"""

from typing import TypedDict


class TypedDictHealthStatus(TypedDict):
    """TypedDict for health status dictionary.

    Used by MixinHealthCheck.get_health_status() to provide precise typing
    for the returned health status dictionary.

    Attributes:
        node_id: Node identifier string
        is_healthy: Boolean health status
        status: Health status string ("healthy", "degraded", "unhealthy")
        health_score: Numeric health score (0.0 to 1.0)
        issues: List of issue message strings
    """

    node_id: str
    is_healthy: bool
    status: str
    health_score: float
    issues: list[str]


__all__ = ["TypedDictHealthStatus"]
