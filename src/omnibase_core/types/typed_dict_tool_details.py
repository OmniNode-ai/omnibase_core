"""
TypedDict for tool details within alert data.

Provides type-safe structure for tool details from missing tool tracking.
"""

from typing import TypedDict


class TypedDictToolDetails(TypedDict):
    """Type-safe structure for tool details within alert data."""

    name: str
    expected_type: str
    category: str
    criticality: str


__all__ = ["TypedDictToolDetails"]
