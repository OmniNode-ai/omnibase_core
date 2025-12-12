"""
TypedDict for alert system data.

Provides type-safe structure for alert data from missing tool tracking.
"""

from typing import TypedDict

from .typed_dict_alert_metadata import TypedDictAlertMetadata
from .typed_dict_operational_impact import TypedDictOperationalImpact
from .typed_dict_tool_details import TypedDictToolDetails


class TypedDictAlertData(TypedDict):
    """Type-safe structure for alert system data."""

    alert_level: str
    title: str
    description: str
    tool_details: TypedDictToolDetails
    impact_assessment: TypedDictOperationalImpact
    recovery_recommendations: list[str]
    metadata: TypedDictAlertMetadata


__all__ = ["TypedDictAlertData"]
