"""
TypedDict for alert metadata.

Provides type-safe structure for alert metadata from missing tool tracking.
"""

from typing import TypedDict


class TypedDictAlertMetadata(TypedDict):
    """Type-safe structure for alert metadata."""

    reason_category: str
    detection_count: int | None
    first_detected: str | None


__all__ = ["TypedDictAlertMetadata"]
