from __future__ import annotations

"""
TypedDict for event information.
"""


from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictEventInfo(TypedDict):
    """TypedDict for event information."""

    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    correlation_id: NotRequired[UUID]
    sequence_number: NotRequired[int]


__all__ = ["TypedDictEventInfo"]
