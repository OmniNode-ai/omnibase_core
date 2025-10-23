from __future__ import annotations

from typing import TypedDict

"""
Timestamp data structure.
"""

from datetime import datetime


class TypedDictTimestampData(TypedDict):
    """Timestamp data structure."""

    last_modified: datetime | None
    last_validated: datetime | None


__all__ = ["TypedDictTimestampData"]
