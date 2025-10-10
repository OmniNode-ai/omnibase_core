from __future__ import annotations

from typing import Dict, TypedDict

"""
Timestamp data structure.
"""


from datetime import datetime
from typing import TypedDict


class TypedDictTimestampData(TypedDict):
    """Timestamp data structure."""

    last_modified: datetime | None
    last_validated: datetime | None


__all__ = ["ModelTypedDictTimestampData"]
