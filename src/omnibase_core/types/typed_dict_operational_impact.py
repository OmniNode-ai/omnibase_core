"""
TypedDict for operational impact assessment.

Provides type-safe structure for operational impact assessment from missing tool tracking.
"""

from typing import TypedDict


class TypedDictOperationalImpact(TypedDict):
    """Type-safe structure for operational impact assessment."""

    business_impact_score: float
    severity_level: str
    affected_operations_count: int
    requires_immediate_attention: bool
    estimated_downtime: str
    user_experience_impact: str
    system_stability_risk: str


__all__ = ["TypedDictOperationalImpact"]
