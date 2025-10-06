from __future__ import annotations

import uuid

"""
TypedDict for event information.
"""


from datetime import datetime
from typing import TypedDict
from uuid import UUID


class TypedDictEventInfo(TypedDict):
    """TypedDict for event information."""

    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    correlation_id: NotRequired[UUID]
    sequence_number: NotRequired[int]
