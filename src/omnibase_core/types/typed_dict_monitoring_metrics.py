"""
TypedDict for monitoring system metrics.

Provides type-safe structure for monitoring metrics from missing tool tracking.
"""

from typing import TypedDict


class TypedDictMonitoringMetrics(TypedDict):
    """Type-safe structure for monitoring system metrics."""

    tool_name: str
    reason_category: str
    criticality: str
    tool_category: str
    severity_level: str
    business_impact_score: float
    requires_immediate_attention: bool
    is_critical_tool: bool
    is_recoverable: bool
    fix_complexity: str
    detection_count: int
    affected_operations_count: int
    has_alternatives: bool
    has_dependencies: bool
    first_detected: str | None


__all__ = ["TypedDictMonitoringMetrics"]
