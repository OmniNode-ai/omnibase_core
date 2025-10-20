"""
TypedDict for timestamp update data.

Strongly-typed representation for timestamp data updates.
Follows ONEX one-model-per-file and TypedDict naming conventions.
"""

from datetime import datetime
from typing import TypedDict


class TypedDictTimestampUpdateData(TypedDict, total=False):
    """Strongly-typed structure for timestamp data updates."""

    created_at: datetime
    updated_at: datetime
    last_accessed: datetime
    deprecated_at: datetime


__all__ = ["TypedDictTimestampUpdateData"]
