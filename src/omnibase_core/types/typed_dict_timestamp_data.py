"""
Timestamp data structure.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict


class TypedDictTimestampData(TypedDict):
    last_modified: datetime | None
    last_validated: datetime | None


__all__ = ["TypedDictTimestampData"]
