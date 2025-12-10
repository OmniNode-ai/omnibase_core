from __future__ import annotations

"""
TypedDict for audit information.
"""


from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictAuditInfo(TypedDict):
    """TypedDict for audit information."""

    action: str
    resource: str
    user_id: UUID
    timestamp: datetime
    ip_address: NotRequired[str]
    user_agent: NotRequired[str]
    outcome: str  # "success", "failure", "partial"


__all__ = ["TypedDictAuditInfo"]
