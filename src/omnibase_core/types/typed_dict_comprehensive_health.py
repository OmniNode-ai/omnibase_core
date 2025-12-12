"""TypedDict for comprehensive health status information."""

from __future__ import annotations

from typing import TypedDict


class TypedDictComprehensiveHealth(TypedDict):
    """
    TypedDict for comprehensive health status.

    Aggregates health status from multiple component checks.

    Attributes:
        overall_status: Overall health status ("healthy" or "degraded")
        component_checks: Dictionary mapping component names to health status
        failing_components: List of component names that are failing
        healthy_count: Number of healthy components
        total_components: Total number of components checked
        timestamp: ISO-formatted timestamp of the health check
    """

    overall_status: str
    component_checks: dict[str, bool]
    failing_components: list[str]
    healthy_count: int
    total_components: int
    timestamp: str


__all__ = ["TypedDictComprehensiveHealth"]
