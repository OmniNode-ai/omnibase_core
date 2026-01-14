"""
TypedDict for event information.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictEventInfo(TypedDict):
    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    correlation_id: NotRequired[UUID]
    sequence_number: NotRequired[int]


__all__ = ["TypedDictEventInfo"]
