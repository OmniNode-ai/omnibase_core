"""
TypedDict for connection information.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict
from uuid import UUID


class TypedDictConnectionInfo(TypedDict):
    connection_id: UUID
    connection_type: str
    status: str  # "connected", "disconnected", "error"
    established_at: datetime
    last_activity: datetime
    bytes_sent: int
    bytes_received: int


__all__ = ["TypedDictConnectionInfo"]
